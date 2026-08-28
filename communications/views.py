from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Count, F, OuterRef, Prefetch, Q, Subquery
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone

from exchanges.models import Session

from .models import CallSignal, ConversationParticipant, Message


def _membership_queryset(user):
    latest_messages = Message.objects.filter(
        conversation_id=OuterRef('conversation_id')
    ).order_by('-created_at')
    unread_filter = ~Q(conversation__messages__sender=user) & (
        Q(last_read_at__isnull=True)
        | Q(conversation__messages__created_at__gt=F('last_read_at'))
    )
    missed_call_filter = ~Q(conversation__call_events__caller=user) & Q(
        conversation__call_events__status='missed',
    ) & (
        Q(last_read_at__isnull=True)
        | Q(conversation__call_events__ended_at__gt=F('last_read_at'))
    )
    return ConversationParticipant.objects.filter(user=user).select_related(
        'conversation', 'conversation__exchange'
    ).prefetch_related(
        'conversation__conversation_participants__user__profile',
        Prefetch(
            'conversation__exchange__sessions',
            queryset=Session.objects.select_related('offer__skill').order_by('scheduled_start'),
        ),
    ).annotate(
        last_message_text=Subquery(latest_messages.values('content')[:1]),
        last_message_at=Subquery(latest_messages.values('created_at')[:1]),
        unread_message_count=Count(
            'conversation__messages', filter=unread_filter, distinct=True,
        ),
        unread_call_count=Count(
            'conversation__call_events', filter=missed_call_filter, distinct=True,
        ),
    ).order_by(F('last_message_at').desc(nulls_last=True), '-conversation__updated_at')


@login_required(login_url='accounts:login')
def conversation_list(request):
    memberships = list(_membership_queryset(request.user))
    for membership in memberships:
        membership.unread_count = membership.unread_message_count + membership.unread_call_count
        participants = membership.conversation.conversation_participants.all()
        membership.other_user = next(
            (item.user for item in participants if item.user_id != request.user.pk), None
        )
        membership.room_session = next(
            iter(membership.conversation.exchange.sessions.all()), None
        ) if membership.conversation.exchange_id else None
    return render(request, 'communications-templates/conversation_list.html', {
        'memberships': memberships,
    })


@login_required(login_url='accounts:login')
def open_conversation(request, pk):
    membership = ConversationParticipant.objects.filter(
        conversation_id=pk, user=request.user,
    ).select_related('conversation__exchange').first()
    if not membership or not membership.conversation.exchange_id:
        return redirect('communications:conversation_list')
    session = membership.conversation.exchange.sessions.order_by('scheduled_start').first()
    if not session:
        return redirect('communications:conversation_list')
    return redirect('exchanges:session_room', pk=session.pk)


@login_required(login_url='accounts:login')
def incoming_call(request):
    cutoff = timezone.now() - timedelta(seconds=30)
    signal = CallSignal.objects.filter(
        Q(session__learner=request.user) | Q(session__provider=request.user),
        signal_type='offer', created_at__gte=cutoff,
    ).exclude(sender=request.user).select_related('sender', 'session').order_by('-id').first()
    if not signal:
        return JsonResponse({'call': None})
    if CallSignal.objects.filter(
        session=signal.session, signal_type='hangup', created_at__gt=signal.created_at,
    ).exists():
        return JsonResponse({'call': None})
    payload = signal.payload or {}
    return JsonResponse({'call': {
        'id': signal.pk,
        'caller': signal.sender.get_full_name() or signal.sender.get_username(),
        'media': payload.get('media', 'audio'),
        'room_url': reverse('exchanges:session_room', args=[signal.session_id]),
        'signals_url': reverse('exchanges:room_signals', args=[signal.session_id]),
    }})
