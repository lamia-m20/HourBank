import json
import uuid
from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.utils import timezone
from django.utils.translation import gettext as _
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from skills.models import SkillOffer
from communications.models import (
    CallEvent, CallSignal, Conversation, ConversationParticipant,
    ConversationSystemEvent, Message, Notification,
)
from .services import (
    accept_exchange_request, cancel_exchange, confirm_session_completion,
    finish_teaching, report_session_issue,
)
from .models import ExchangeRequest, Session


@login_required(login_url='accounts:login')
def exchange_requests(request):
    sent = ExchangeRequest.objects.filter(requester=request.user).select_related('offer', 'provider')
    received = list(ExchangeRequest.objects.filter(offer__user=request.user).select_related(
        'offer__skill', 'requester', 'requester__profile'
    ))
    unseen_ids = [
        item.pk for item in received
        if item.status == 'pending' and item.provider_seen_at is None
    ]
    for item in received:
        item.is_new_for_provider = item.pk in unseen_ids
        item.requester_offers = SkillOffer.objects.filter(
            user=item.requester, is_active=True
        ).select_related('skill')
    response = render(request, 'exchanges-templates/requests.html', {'sent': sent, 'received': received})
    if unseen_ids:
        ExchangeRequest.objects.filter(
            pk__in=unseen_ids, offer__user=request.user, provider_seen_at__isnull=True,
        ).update(provider_seen_at=timezone.now())
    return response


@login_required(login_url='accounts:login')
def request_notifications(request):
    unseen = ExchangeRequest.objects.filter(
        offer__user=request.user, status='pending', provider_seen_at__isnull=True,
    )
    latest = unseen.select_related('requester', 'offer__skill').order_by('-created_at').first()
    return JsonResponse({
        'exchange_requests': unseen.count(),
        'latest_request': ({
            'id': latest.pk,
            'requester': latest.requester.get_full_name() or latest.requester.get_username(),
            'skill': latest.offer.skill.name,
            'url': reverse('exchanges:requests'),
        } if latest else None),
    })


@login_required(login_url='accounts:login')
def sessions(request):
    items = Session.objects.filter(
        Q(learner=request.user) | Q(provider=request.user)
    ).select_related('exchange', 'offer', 'learner', 'provider')
    return render(request, 'exchanges-templates/sessions.html', {'sessions': items})


@login_required(login_url='accounts:login')
@require_POST
def accept_request(request, pk):
    swap_offer = None
    if request.POST.get('mode') == 'swap':
        pending_exchange = get_object_or_404(
            ExchangeRequest, pk=pk, offer__user=request.user, status='pending'
        )
        swap_offer = get_object_or_404(
            SkillOffer, pk=request.POST.get('swap_offer'),
            user=pending_exchange.requester, is_active=True,
        )
    try:
        ExchangeRequest.objects.filter(
            pk=pk, offer__user=request.user, provider_seen_at__isnull=True,
        ).update(provider_seen_at=timezone.now())
        accept_exchange_request(exchange_id=pk, provider=request.user, swap_offer=swap_offer)
        messages.success(request, 'Exchange request accepted successfully.')
    except (ValidationError, ExchangeRequest.DoesNotExist) as exc:
        message = exc.messages[0] if isinstance(exc, ValidationError) else 'Request not found.'
        messages.error(request, message)
    return redirect('exchanges:requests')


@login_required(login_url='accounts:login')
@require_POST
def reject_request(request, pk):
    exchange = get_object_or_404(ExchangeRequest, pk=pk, offer__user=request.user, status='pending')
    exchange.status = 'rejected'
    exchange.provider_seen_at = timezone.now()
    exchange.save(update_fields=['status', 'provider_seen_at', 'updated_at'])
    return redirect('exchanges:requests')


def _participant_session(request, pk):
    return get_object_or_404(
        Session.objects.select_related(
            'exchange__conversation', 'offer__skill', 'learner__profile', 'provider__profile'
        ).filter(Q(learner=request.user) | Q(provider=request.user)), pk=pk,
    )


@login_required(login_url='accounts:login')
def session_room(request, pk):
    session = _participant_session(request, pk)
    if session.status == 'scheduled':
        session.status = 'in_progress'
        session.started_at = timezone.now()
        session.save(update_fields=['status', 'started_at', 'updated_at'])
        ExchangeRequest.objects.filter(pk=session.exchange_id, status='accepted').update(
            status='in_progress'
        )
    other_user = session.provider if request.user.pk == session.learner_id else session.learner
    conversation, _ = Conversation.objects.get_or_create(exchange=session.exchange)
    ConversationParticipant.objects.bulk_create([
        ConversationParticipant(conversation=conversation, user=session.learner),
        ConversationParticipant(conversation=conversation, user=session.provider),
    ], ignore_conflicts=True)
    ConversationParticipant.objects.filter(
        conversation=conversation, user=request.user
    ).update(last_read_at=timezone.now())
    return render(request, 'exchanges-templates/session_room.html', {
        'session': session, 'other_user': other_user,
        'webrtc_ice_servers': settings.WEBRTC_ICE_SERVERS,
    })


@login_required(login_url='accounts:login')
def room_messages(request, pk):
    session = _participant_session(request, pk)
    conversation, _ = Conversation.objects.get_or_create(exchange=session.exchange)
    if request.method == 'POST':
        try:
            data = json.loads(request.body or '{}')
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON.'}, status=400)
        content = str(data.get('content', '')).strip()
        if not content or len(content) > 4000:
            return JsonResponse({'error': 'Message content is required.'}, status=400)
        try:
            client_id = uuid.UUID(str(data.get('client_id'))) if data.get('client_id') else None
        except (ValueError, TypeError, AttributeError):
            return JsonResponse({'error': 'Invalid client message ID.'}, status=400)
        message, created = Message.objects.get_or_create(
            conversation=conversation, sender=request.user, client_id=client_id,
            defaults={'content': content},
        ) if client_id else (Message.objects.create(
            conversation=conversation, sender=request.user, content=content,
        ), True)
        if created:
            recipient = conversation.participants.exclude(pk=request.user.pk).first()
            if recipient:
                Notification.objects.create(
                    user=recipient, notification_type='message', title='New message',
                    message=content[:250],
                    target_url=reverse('exchanges:session_room', args=[session.pk]),
                )
        return JsonResponse({'message': _message_payload(message)}, status=201 if created else 200)
    after = request.GET.get('after', '0')
    try:
        after = int(after)
    except ValueError:
        after = 0
    read_at = timezone.now()
    items = list(conversation.messages.filter(pk__gt=after).select_related(
        'sender', 'sender__profile'
    )[:100])
    ConversationParticipant.objects.filter(
        conversation=conversation, user=request.user
    ).update(last_read_at=read_at)
    call_events = conversation.call_events.select_related('caller').order_by('started_at')[:100]
    system_events = conversation.system_events.select_related('session').order_by('created_at')[:100]
    return JsonResponse({
        'messages': [_message_payload(item) for item in items],
        'call_events': [_call_event_payload(item, request.user.pk) for item in call_events],
        'system_events': [_system_event_payload(item) for item in system_events],
    })


def _message_payload(message):
    profile = getattr(message.sender, 'profile', None)
    avatar_url = ''
    if profile and profile.profile_image:
        avatar_url = profile.profile_image.url
    return {
        'id': message.pk, 'sender_id': message.sender_id,
        'sender': message.sender.get_full_name() or message.sender.get_username(),
        'sender_avatar': avatar_url,
        'content': message.content, 'text': message.content,
        'created_at': message.created_at.isoformat(),
    }


def _call_event_payload(call, viewer_id):
    return {
        'id': call.pk, 'caller_id': call.caller_id,
        'call_type': call.call_type, 'status': call.status,
        'started_at': call.started_at.isoformat(),
        'answered_at': call.answered_at.isoformat() if call.answered_at else None,
        'ended_at': call.ended_at.isoformat() if call.ended_at else None,
        'duration_seconds': call.duration_seconds,
        'is_incoming': call.caller_id != viewer_id,
    }


def _system_event_payload(event):
    return {
        'id': event.pk, 'event_type': event.event_type,
        'data': event.data, 'created_at': event.created_at.isoformat(),
    }


def _update_call_event(session, user, signal_type, payload):
    conversation, _ = Conversation.objects.get_or_create(exchange=session.exchange)
    if signal_type == 'offer':
        try:
            client_id = uuid.UUID(str(payload.get('client_call_id'))) if payload.get('client_call_id') else uuid.uuid4()
        except (ValueError, TypeError, AttributeError):
            raise ValueError('Invalid call ID.')
        call, _ = CallEvent.objects.get_or_create(
            client_id=client_id,
            defaults={
                'conversation': conversation, 'session': session, 'caller': user,
                'call_type': payload.get('media') if payload.get('media') in {'audio', 'video'} else 'audio',
            },
        )
        if call.session_id != session.pk or call.caller_id != user.pk:
            raise ValueError('Invalid call ID.')
        payload['call_id'] = call.pk
        return call
    call_id = payload.get('call_id')
    if not call_id:
        return None
    with transaction.atomic():
        call = CallEvent.objects.select_for_update().filter(
            pk=call_id, session=session, conversation=conversation,
        ).first()
        if not call:
            raise ValueError('Invalid call event.')
        now = timezone.now()
        if signal_type == 'answer' and call.status == 'ringing' and user.pk != call.caller_id:
            call.status, call.answered_at = 'answered', now
            call.save(update_fields=['status', 'answered_at', 'updated_at'])
        elif signal_type == 'hangup' and call.status in {'ringing', 'answered'}:
            reason = payload.get('reason')
            if call.status == 'answered':
                call.status = 'ended'
                call.duration_seconds = max(0, int((now - call.answered_at).total_seconds()))
            elif reason == 'declined' and user.pk != call.caller_id:
                call.status = 'declined'
            elif reason == 'missed':
                call.status = 'missed'
            else:
                call.status = 'cancelled'
            call.ended_at = now
            call.save(update_fields=['status', 'ended_at', 'duration_seconds', 'updated_at'])
        return call


@login_required(login_url='accounts:login')
def room_signals(request, pk):
    session = _participant_session(request, pk)
    session.call_signals.filter(created_at__lt=timezone.now() - timedelta(hours=1)).delete()
    if request.method == 'POST':
        if len(request.body) > 100_000:
            return JsonResponse({'error': 'Signal payload is too large.'}, status=413)
        try:
            data = json.loads(request.body or '{}')
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON.'}, status=400)
        signal_type = data.get('type')
        if signal_type not in dict(CallSignal.SIGNAL_TYPES):
            return JsonResponse({'error': 'Invalid signal type.'}, status=400)
        payload = data.get('payload') or {}
        try:
            call_event = _update_call_event(session, request.user, signal_type, payload)
        except ValueError as exc:
            return JsonResponse({'error': str(exc)}, status=400)
        if signal_type == 'hangup':
            session.call_signals.all().delete()
        signal = CallSignal.objects.create(
            session=session, sender=request.user, signal_type=signal_type,
            payload=payload,
        )
        return JsonResponse({
            'id': signal.pk,
            'call_event': _call_event_payload(call_event, request.user.pk) if call_event else None,
        }, status=201)
    try:
        after = int(request.GET.get('after', '0'))
    except ValueError:
        after = 0
    signals = session.call_signals.filter(pk__gt=after).exclude(sender=request.user)[:100]
    return JsonResponse({'ice_servers': settings.WEBRTC_ICE_SERVERS, 'signals': [
        {'id': item.pk, 'type': item.signal_type, 'payload': item.payload}
        for item in signals
    ]})


def _service_action(request, service, success, **kwargs):
    try:
        service(**kwargs)
        messages.success(request, success)
    except (ValidationError, Session.DoesNotExist, ExchangeRequest.DoesNotExist) as exc:
        message = exc.messages[0] if isinstance(exc, ValidationError) else 'Session not found.'
        messages.error(request, message)


@login_required(login_url='accounts:login')
@require_POST
def finish_session(request, pk):
    _service_action(request, finish_teaching, 'Teaching finished. Awaiting learner confirmation.',
                    session_id=pk, provider=request.user)
    return redirect('exchanges:session_room', pk=pk)


@login_required(login_url='accounts:login')
@require_POST
def confirm_session(request, pk):
    _service_action(request, confirm_session_completion, 'Session completed and held hours transferred.',
                    session_id=pk, learner=request.user)
    return redirect('exchanges:session_room', pk=pk)


@login_required(login_url='accounts:login')
@require_POST
def report_issue(request, pk):
    _service_action(request, report_session_issue,
                    _('Your issue has been recorded. The held hours will not be transferred until the case is reviewed.'),
                    session_id=pk, learner=request.user,
                    reason=request.POST.get('reason', ''),
                    details=request.POST.get('details', ''))
    return redirect('exchanges:session_room', pk=pk)


@login_required(login_url='accounts:login')
@require_POST
def cancel_request(request, pk):
    _service_action(request, cancel_exchange, 'Exchange cancelled and held hours released.',
                    exchange_id=pk, user=request.user)
    return redirect('exchanges:requests')
