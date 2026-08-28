from datetime import datetime, timedelta

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from communications.models import (
    Conversation, ConversationParticipant, ConversationSystemEvent, Dispute, Notification,
)
from wallet.models import HourHold, HourTransaction, HourWallet

from .models import ExchangeHistory, ExchangeRequest, Session, SessionConfirmation


def _locked_wallets(users):
    user_ids = sorted(user.pk for user in users)
    wallets = {
        wallet.user_id: wallet for wallet in HourWallet.objects.select_for_update()
        .filter(user_id__in=user_ids).select_related('user').order_by('user_id')
    }
    for user in users:
        if user.pk not in wallets:
            wallets[user.pk] = HourWallet.objects.create(user=user)
    return wallets


def _scheduled_times(exchange, offer):
    if exchange.requested_date and exchange.requested_time:
        start = timezone.make_aware(
            datetime.combine(exchange.requested_date, exchange.requested_time),
            timezone.get_current_timezone(),
        )
    else:
        start = timezone.now()
    return start, start + timedelta(minutes=offer.session_duration_minutes)


def _create_session_direction(*, exchange, learner, provider, offer):
    start, end = _scheduled_times(exchange, offer)
    return Session.objects.create(
        exchange=exchange, learner=learner, provider=provider, offer=offer,
        scheduled_start=start, scheduled_end=end,
        delivery_method=offer.delivery_method, status='scheduled',
    )


@transaction.atomic
def accept_exchange_request(*, exchange_id, provider, swap_offer=None):
    exchange = ExchangeRequest.objects.select_for_update().select_related(
        'offer__skill', 'requester', 'provider'
    ).get(pk=exchange_id, offer__user=provider)
    if exchange.status != 'pending':
        raise ValidationError('This request has already been processed.')
    if swap_offer and (swap_offer.user_id != exchange.requester_id or not swap_offer.is_active):
        raise ValidationError('The selected exchange offer is not available.')

    _create_session_direction(
        exchange=exchange, learner=exchange.requester,
        provider=provider, offer=exchange.offer,
    )
    if swap_offer:
        _create_session_direction(
            exchange=exchange, learner=provider,
            provider=exchange.requester, offer=swap_offer,
        )
    exchange.provider = provider
    exchange.reverse_offer = swap_offer
    exchange.status = 'accepted'
    exchange.save(update_fields=['provider', 'reverse_offer', 'status', 'updated_at'])
    conversation, _ = Conversation.objects.get_or_create(exchange=exchange)
    ConversationParticipant.objects.bulk_create([
        ConversationParticipant(conversation=conversation, user=exchange.requester),
        ConversationParticipant(conversation=conversation, user=provider),
    ], ignore_conflicts=True)
    ExchangeHistory.objects.create(
        exchange=exchange, changed_by=provider, old_status='pending',
        new_status='accepted', notes='skill_exchange' if swap_offer else 'teaching_only',
    )
    return exchange


@transaction.atomic
def finish_teaching(*, session_id, provider):
    session = Session.objects.select_for_update().select_related('exchange').get(pk=session_id)
    if session.provider_id != provider.pk:
        raise ValidationError('Only the skill provider can finish teaching.')
    if session.status not in ('scheduled', 'in_progress'):
        raise ValidationError('This session cannot be finished in its current state.')
    session.status = 'awaiting_confirmation'
    session.save(update_fields=['status', 'updated_at'])
    exchange = ExchangeRequest.objects.select_for_update().get(pk=session.exchange_id)
    exchange.status = 'awaiting_confirmation'
    exchange.save(update_fields=['status', 'updated_at'])
    return session


@transaction.atomic
def confirm_session_completion(*, session_id, learner):
    session = Session.objects.select_for_update().get(pk=session_id)
    if session.learner_id != learner.pk:
        raise ValidationError('Only the learner can confirm completion.')
    if session.status == 'completed':
        raise ValidationError('This session has already been confirmed.')
    if session.status != 'awaiting_confirmation':
        raise ValidationError('This session is not awaiting confirmation.')
    if session.disputes.filter(status__in=('open', 'under_review')).exists():
        raise ValidationError('A reported issue must be reviewed before any reward can be added.')
    if session.uses_reward_system:
        if session.reward_processed:
            raise ValidationError('The reward for this session has already been processed.')
        payee_wallet = _locked_wallets((session.provider,))[session.provider_id]
        amount = session.offer.hour_cost
        payee_wallet.available_balance += amount
        payee_wallet.total_earned += amount
        payee_wallet.save(update_fields=['available_balance', 'total_earned', 'updated_at'])
        HourTransaction.objects.create(
            wallet=payee_wallet, exchange=session.exchange, transaction_type='earned',
            direction='credit', amount=amount, balance_after=payee_wallet.available_balance,
            description=f'Teaching {session.offer.skill.name} to {learner.get_username()}',
        )
        session.reward_processed = True
        session.rewarded_at = timezone.now()
    else:
        _capture_legacy_hold(session=session, learner=learner)
        amount = session.offer.hour_cost

    SessionConfirmation.objects.update_or_create(
        session=session, user=learner,
        defaults={'confirmed': True, 'issue_reported': False},
    )
    session.status = 'completed'
    session.completed_at = timezone.now()
    session.save(update_fields=[
        'status', 'completed_at', 'reward_processed', 'rewarded_at', 'updated_at',
    ])
    provider_profile = session.provider.profile
    type(provider_profile).objects.filter(pk=provider_profile.pk).update(
        completed_sessions=F('completed_sessions') + 1)
    exchange = ExchangeRequest.objects.select_for_update().get(pk=session.exchange_id)
    conversation, _ = Conversation.objects.get_or_create(exchange=exchange)
    ConversationSystemEvent.objects.get_or_create(
        session=session, event_type='reward',
        defaults={'conversation': conversation, 'actor': learner, 'data': {
            'amount': str(amount),
            'provider_name': session.provider.get_full_name() or session.provider.get_username(),
        }},
    )
    exchange.status = (
        'completed' if not exchange.sessions.exclude(status='completed').exists()
        else 'awaiting_confirmation'
    )
    exchange.save(update_fields=['status', 'updated_at'])
    return session


def _capture_legacy_hold(*, session, learner):
    hold = HourHold.objects.select_for_update().select_related('wallet__user').get(
        exchange=session.exchange, wallet__user=learner, payee=session.provider,
        offer=session.offer, status='active',
    )
    wallets = _locked_wallets((learner, session.provider))
    payer_wallet = wallets[learner.pk]
    payee_wallet = wallets[session.provider_id]
    if payer_wallet.held_balance < hold.amount:
        raise ValidationError('The held balance is inconsistent.')
    payer_wallet.held_balance -= hold.amount
    payer_wallet.total_spent += hold.amount
    payee_wallet.available_balance += hold.amount
    payee_wallet.total_earned += hold.amount
    payer_wallet.save(update_fields=['held_balance', 'total_spent', 'updated_at'])
    payee_wallet.save(update_fields=['available_balance', 'total_earned', 'updated_at'])
    hold.status = 'captured'
    hold.released_at = timezone.now()
    hold.save(update_fields=['status', 'released_at'])
    HourTransaction.objects.create(
        wallet=payer_wallet, exchange=session.exchange, transaction_type='spent',
        direction='debit', amount=hold.amount, balance_after=payer_wallet.available_balance,
        description=f'Learning {session.offer.skill.name} from {session.provider.get_username()}',
    )
    HourTransaction.objects.create(
        wallet=payee_wallet, exchange=session.exchange, transaction_type='earned',
        direction='credit', amount=hold.amount, balance_after=payee_wallet.available_balance,
        description=f'Teaching {session.offer.skill.name} to {learner.get_username()}',
    )


@transaction.atomic
def report_session_issue(*, session_id, learner, reason='incomplete', details='', notes=None):
    session = Session.objects.select_for_update().select_related('exchange').get(pk=session_id)
    if session.learner_id != learner.pk:
        raise ValidationError('Only the learner can report a session issue.')
    if session.disputes.filter(status__in=('open', 'under_review')).exists():
        raise ValidationError('An issue has already been reported for this session.')
    if session.status != 'awaiting_confirmation':
        raise ValidationError('This session is not awaiting confirmation.')
    if reason not in {value for value, _ in Dispute.REASON_CHOICES}:
        raise ValidationError('Please select a valid issue reason.')
    if notes is not None and not details:
        details = notes
    details = (details or '').strip()
    if reason == 'other' and not details:
        raise ValidationError('Please briefly describe the issue.')
    if len(details) > 3000:
        raise ValidationError('Issue details are too long.')
    SessionConfirmation.objects.update_or_create(
        session=session, user=learner,
        defaults={'confirmed': False, 'issue_reported': True, 'notes': details},
    )
    dispute = Dispute.objects.create(
        exchange=session.exchange, session=session, opened_by=learner,
        against_user=session.provider, reason=reason, description=details,
    )
    session.status = 'disputed'
    session.save(update_fields=['status', 'updated_at'])
    ExchangeRequest.objects.filter(pk=session.exchange_id).update(status='disputed')
    conversation, _ = Conversation.objects.get_or_create(exchange=session.exchange)
    ConversationSystemEvent.objects.get_or_create(
        session=session, event_type='dispute',
        defaults={'conversation': conversation, 'actor': learner, 'data': {
            'reason': str(dispute.get_reason_display()), 'details': details,
        }},
    )
    Notification.objects.create(
        user=session.provider, notification_type='system', title='Session issue recorded',
        message='An issue was recorded for this session. No reward will be added pending review.',
        target_url=f'/exchanges/session/{session.pk}/room/',
    )
    return session


@transaction.atomic
def cancel_exchange(*, exchange_id, user):
    exchange = ExchangeRequest.objects.select_for_update().get(pk=exchange_id)
    if user.pk not in (exchange.requester_id, exchange.provider_id):
        raise ValidationError('You are not a participant in this exchange.')
    if exchange.status in ('completed', 'cancelled', 'disputed'):
        raise ValidationError('This exchange cannot be cancelled.')
    holds = list(HourHold.objects.select_for_update().filter(exchange=exchange, status='active'))
    wallet_ids = sorted({hold.wallet_id for hold in holds})
    wallets = {w.pk: w for w in HourWallet.objects.select_for_update().filter(pk__in=wallet_ids)}
    for hold in holds:
        wallet = wallets[hold.wallet_id]
        wallet.available_balance += hold.amount
        wallet.held_balance -= hold.amount
        wallet.save(update_fields=['available_balance', 'held_balance', 'updated_at'])
        hold.status = 'released'
        hold.released_at = timezone.now()
        hold.save(update_fields=['status', 'released_at'])
        HourTransaction.objects.create(
            wallet=wallet, exchange=exchange, transaction_type='release', direction='credit',
            amount=hold.amount, balance_after=wallet.available_balance,
            description='Released after session cancellation',
        )
    exchange.sessions.exclude(status='completed').update(status='cancelled')
    exchange.status = 'cancelled'
    exchange.save(update_fields=['status', 'updated_at'])
    return exchange
