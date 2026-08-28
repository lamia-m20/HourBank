from decimal import Decimal
from datetime import timedelta
import uuid

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.contrib.staticfiles import finders
from django.urls import reverse
from django.utils import timezone

from accounts.models import UserProfile
from communications.models import (
    CallEvent, ConversationParticipant, ConversationSystemEvent, Dispute, Message, Notification,
)
from skills.models import Skill, SkillCategory, SkillOffer
from wallet.models import HourHold, HourTransaction

from .models import ExchangeRequest
from .services import (
    accept_exchange_request, cancel_exchange, confirm_session_completion,
    finish_teaching, report_session_issue,
)


class ExchangeWorkflowTests(TestCase):
    def setUp(self):
        self.lamia = User.objects.create_user('lamia', password='pass12345')
        self.sara = User.objects.create_user('sara', password='pass12345')
        self.outsider = User.objects.create_user('outsider', password='pass12345')
        for user in (self.lamia, self.sara, self.outsider):
            UserProfile.objects.create(user=user)
        category = SkillCategory.objects.first() or SkillCategory.objects.create(name='Technology')
        python = Skill.objects.create(category=category, name='Python')
        english = Skill.objects.create(category=category, name='English')
        self.python_offer = SkillOffer.objects.create(
            user=self.lamia, skill=python, title='Learn Python', description='Python', hour_cost=1,
        )
        self.english_offer = SkillOffer.objects.create(
            user=self.sara, skill=english, title='Learn English', description='English', hour_cost=1,
        )

    def make_request(self):
        return ExchangeRequest.objects.create(
            requester=self.sara, provider=self.lamia, offer=self.python_offer,
            requested_hours=self.python_offer.hour_cost,
        )

    def balances(self):
        self.lamia.hour_wallet.refresh_from_db()
        self.sara.hour_wallet.refresh_from_db()
        return (
            self.lamia.hour_wallet.available_balance, self.lamia.hour_wallet.held_balance,
            self.sara.hour_wallet.available_balance, self.sara.hour_wallet.held_balance,
        )

    def totals(self):
        self.lamia.hour_wallet.refresh_from_db()
        self.sara.hour_wallet.refresh_from_db()
        return (
            self.lamia.hour_wallet.total_earned, self.lamia.hour_wallet.total_spent,
            self.sara.hour_wallet.total_earned, self.sara.hour_wallet.total_spent,
        )

    def test_accept_does_not_move_hours_or_create_hold(self):
        exchange = self.make_request()
        accept_exchange_request(exchange_id=exchange.pk, provider=self.lamia)
        self.assertEqual(self.balances(), (Decimal('20'), 0, Decimal('20'), 0))
        self.assertFalse(HourHold.objects.filter(exchange=exchange).exists())
        self.assertFalse(HourTransaction.objects.filter(exchange=exchange, transaction_type='hold').exists())
        self.assertFalse(HourTransaction.objects.filter(exchange=exchange, transaction_type='earned').exists())
        self.assertEqual(self.totals(), (0, 0, 0, 0))
        self.assertEqual(exchange.sessions.count(), 1)

    def test_provider_sees_unread_request_badge_then_request_is_marked_seen(self):
        exchange = self.make_request()
        self.client.force_login(self.lamia)
        dashboard = self.client.get(reverse('accounts:dashboard'))
        self.assertEqual(dashboard.context['pending_exchange_requests_count'], 1)
        self.assertContains(dashboard, 'id="exchange-requests-badge"')

        requests_page = self.client.get(reverse('exchanges:requests'))
        self.assertContains(requests_page, 'new-request-badge')
        exchange.refresh_from_db()
        self.assertIsNotNone(exchange.provider_seen_at)

        dashboard = self.client.get(reverse('accounts:dashboard'))
        self.assertEqual(dashboard.context['pending_exchange_requests_count'], 0)
        self.client.force_login(self.sara)
        self.assertEqual(
            self.client.get(reverse('accounts:dashboard')).context['pending_exchange_requests_count'],
            0,
        )

    def test_request_notification_endpoint_is_private_and_reappears_for_new_offer(self):
        first = self.make_request()
        self.client.force_login(self.lamia)
        url = reverse('exchanges:request_notifications')
        payload = self.client.get(url).json()
        self.assertEqual(payload['exchange_requests'], 1)
        self.assertEqual(payload['latest_request']['id'], first.pk)
        self.client.get(reverse('exchanges:requests'))
        self.assertEqual(self.client.get(url).json()['exchange_requests'], 0)

        second_offer = SkillOffer.objects.create(
            user=self.lamia, skill=self.python_offer.skill, title='Advanced Python',
            description='Advanced Python', hour_cost=2,
        )
        second = ExchangeRequest.objects.create(
            requester=self.sara, provider=self.lamia, offer=second_offer, requested_hours=2,
        )
        self.assertEqual(self.client.get(url).json()['latest_request']['id'], second.pk)
        self.client.force_login(self.sara)
        self.assertEqual(self.client.get(url).json()['exchange_requests'], 0)

    def test_provider_finish_does_not_transfer_and_learner_confirmation_does(self):
        exchange = self.make_request()
        accept_exchange_request(exchange_id=exchange.pk, provider=self.lamia)
        session = exchange.sessions.get()
        finish_teaching(session_id=session.pk, provider=self.lamia)
        self.assertEqual(self.balances(), (Decimal('20'), 0, Decimal('20'), 0))
        self.assertEqual(self.totals(), (0, 0, 0, 0))
        for user in (self.lamia, self.sara):
            self.client.force_login(user)
            journey = self.client.get(reverse('accounts:learning_journey'))
            self.assertFalse(journey.context['learned'].exists())
            self.assertFalse(journey.context['taught'].exists())
        confirm_session_completion(session_id=session.pk, learner=self.sara)
        self.assertEqual(self.balances(), (Decimal('21'), 0, Decimal('20'), 0))
        self.assertEqual(self.totals(), (Decimal('1'), 0, 0, 0))
        self.assertFalse(HourHold.objects.filter(exchange=exchange).exists())
        self.assertEqual(HourTransaction.objects.filter(exchange=exchange, transaction_type='spent').count(), 0)
        self.assertEqual(HourTransaction.objects.filter(exchange=exchange, transaction_type='earned').count(), 1)
        self.client.force_login(self.lamia)
        taught = list(self.client.get(reverse('accounts:learning_journey')).context['taught'])
        self.assertEqual([item.pk for item in taught], [session.pk])
        self.client.force_login(self.sara)
        learned = list(self.client.get(reverse('accounts:learning_journey')).context['learned'])
        self.assertEqual([item.pk for item in learned], [session.pk])
        session.refresh_from_db()
        self.assertTrue(session.reward_processed)
        self.assertIsNotNone(session.rewarded_at)
        self.assertEqual(ConversationSystemEvent.objects.filter(session=session, event_type='reward').count(), 1)
        with self.assertRaises(ValidationError):
            confirm_session_completion(session_id=session.pk, learner=self.sara)
        self.assertEqual(self.balances(), (Decimal('21'), 0, Decimal('20'), 0))
        self.assertEqual(HourTransaction.objects.filter(exchange=exchange, transaction_type='spent').count(), 0)
        self.assertEqual(HourTransaction.objects.filter(exchange=exchange, transaction_type='earned').count(), 1)

    def test_only_learner_can_confirm(self):
        exchange = self.make_request()
        accept_exchange_request(exchange_id=exchange.pk, provider=self.lamia)
        session = exchange.sessions.get()
        finish_teaching(session_id=session.pk, provider=self.lamia)
        with self.assertRaises(ValidationError):
            confirm_session_completion(session_id=session.pk, learner=self.lamia)

    def test_swap_holds_and_confirms_each_direction_independently(self):
        exchange = self.make_request()
        accept_exchange_request(
            exchange_id=exchange.pk, provider=self.lamia, swap_offer=self.english_offer,
        )
        self.assertEqual(self.balances(), (Decimal('20'), 0, Decimal('20'), 0))
        english_session = exchange.sessions.get(offer=self.english_offer)
        finish_teaching(session_id=english_session.pk, provider=self.sara)
        confirm_session_completion(session_id=english_session.pk, learner=self.lamia)
        self.assertEqual(self.balances(), (Decimal('20'), 0, Decimal('21'), 0))
        python_session = exchange.sessions.get(offer=self.python_offer)
        finish_teaching(session_id=python_session.pk, provider=self.lamia)
        confirm_session_completion(session_id=python_session.pk, learner=self.sara)
        self.assertEqual(self.balances(), (Decimal('21'), 0, Decimal('21'), 0))
        self.client.force_login(self.lamia)
        journey = self.client.get(reverse('accounts:learning_journey'))
        self.assertEqual([item.pk for item in journey.context['taught']], [python_session.pk])
        self.assertEqual([item.pk for item in journey.context['learned']], [english_session.pk])
        self.client.force_login(self.sara)
        journey = self.client.get(reverse('accounts:learning_journey'))
        self.assertEqual([item.pk for item in journey.context['taught']], [english_session.pk])
        self.assertEqual([item.pk for item in journey.context['learned']], [python_session.pk])

    def test_cancel_releases_hold_without_provider_credit(self):
        exchange = self.make_request()
        accept_exchange_request(exchange_id=exchange.pk, provider=self.lamia)
        cancel_exchange(exchange_id=exchange.pk, user=self.sara)
        self.assertEqual(self.balances(), (Decimal('20'), 0, Decimal('20'), Decimal('0')))
        self.assertFalse(HourHold.objects.filter(exchange=exchange).exists())
        self.assertFalse(HourTransaction.objects.filter(exchange=exchange, transaction_type='earned').exists())

    def test_issue_does_not_move_hours(self):
        exchange = self.make_request()
        accept_exchange_request(exchange_id=exchange.pk, provider=self.lamia)
        session = exchange.sessions.get()
        finish_teaching(session_id=session.pk, provider=self.lamia)
        report_session_issue(session_id=session.pk, learner=self.sara, notes='Not completed')
        self.assertEqual(self.balances(), (Decimal('20'), 0, Decimal('20'), 0))
        session.refresh_from_db()
        self.assertEqual(session.status, 'disputed')
        for user in (self.lamia, self.sara):
            self.client.force_login(user)
            journey = self.client.get(reverse('accounts:learning_journey'))
            self.assertNotIn(session.pk, [item.pk for item in journey.context['learned']])
            self.assertNotIn(session.pk, [item.pk for item in journey.context['taught']])

    def test_learning_journey_refresh_never_duplicates_a_session(self):
        exchange = self.make_request()
        accept_exchange_request(exchange_id=exchange.pk, provider=self.lamia)
        session = exchange.sessions.get()
        finish_teaching(session_id=session.pk, provider=self.lamia)
        confirm_session_completion(session_id=session.pk, learner=self.sara)
        self.client.force_login(self.sara)
        url = reverse('accounts:learning_journey')
        for _ in range(3):
            learned = list(self.client.get(url).context['learned'])
            self.assertEqual([item.pk for item in learned], [session.pk])

    def test_issue_form_records_reason_once_without_reward(self):
        exchange = self.make_request()
        accept_exchange_request(exchange_id=exchange.pk, provider=self.lamia)
        session = exchange.sessions.get()
        finish_teaching(session_id=session.pk, provider=self.lamia)
        self.client.force_login(self.sara)
        room = self.client.get(reverse('exchanges:session_room', args=[session.pk]))
        self.assertContains(room, 'open-issue-dialog')
        response = self.client.post(reverse('exchanges:report_issue', args=[session.pk]), {
            'reason': 'no_teaching', 'details': 'The agreed topic was not covered.',
        }, follow=True)
        self.assertContains(response, 'تم تسجيل المشكلة')
        dispute = Dispute.objects.get(session=session)
        self.assertEqual(dispute.reason, 'no_teaching')
        self.assertEqual(dispute.opened_by, self.sara)
        session.refresh_from_db(); exchange.refresh_from_db()
        self.assertEqual(session.status, 'disputed')
        self.assertEqual(exchange.status, 'disputed')
        self.assertEqual(self.balances(), (Decimal('20'), 0, Decimal('20'), 0))
        self.assertEqual(self.totals(), (0, 0, 0, 0))
        with self.assertRaises(ValidationError):
            report_session_issue(session_id=session.pk, learner=self.sara, reason='technical_issue')
        self.assertEqual(Dispute.objects.filter(session=session).count(), 1)
        self.assertEqual(ConversationSystemEvent.objects.filter(session=session, event_type='dispute').count(), 1)
        self.assertTrue(Notification.objects.filter(user=self.lamia, title='Session issue recorded').exists())

    def test_other_issue_requires_details_and_provider_cannot_report(self):
        exchange = self.make_request()
        accept_exchange_request(exchange_id=exchange.pk, provider=self.lamia)
        session = exchange.sessions.get()
        finish_teaching(session_id=session.pk, provider=self.lamia)
        with self.assertRaises(ValidationError):
            report_session_issue(session_id=session.pk, learner=self.sara, reason='other', details='')
        with self.assertRaises(ValidationError):
            report_session_issue(session_id=session.pk, learner=self.lamia, reason='no_show')
        self.assertFalse(Dispute.objects.filter(session=session).exists())

    def test_room_chat_and_signaling_are_private(self):
        exchange = self.make_request()
        accept_exchange_request(exchange_id=exchange.pk, provider=self.lamia)
        session = exchange.sessions.get()
        room = reverse('exchanges:session_room', args=[session.pk])
        messages_url = reverse('exchanges:room_messages', args=[session.pk])
        signals_url = reverse('exchanges:room_signals', args=[session.pk])
        self.client.force_login(self.outsider)
        self.assertEqual(self.client.get(room).status_code, 404)
        self.assertEqual(self.client.get(messages_url).status_code, 404)
        self.assertEqual(self.client.post(
            messages_url, data='{"content":"intrusion"}', content_type='application/json'
        ).status_code, 404)
        self.assertEqual(self.client.get(signals_url).status_code, 404)
        self.assertEqual(self.client.post(
            signals_url, data='{"type":"offer","payload":{}}', content_type='application/json'
        ).status_code, 404)
        self.client.force_login(self.sara)
        self.assertEqual(self.client.get(room).status_code, 200)
        self.assertContains(self.client.get(reverse('exchanges:requests')), room)
        response = self.client.post(
            messages_url, data='{"content":"Hello Lamia"}', content_type='application/json',
        )
        self.assertEqual(response.status_code, 201)
        first_message_id = response.json()['message']['id']
        self.assertIn('sender_avatar', response.json()['message'])
        self.assertTrue(Message.objects.filter(sender=self.sara, content='Hello Lamia').exists())
        response = self.client.post(
            signals_url, data='{"type":"offer","payload":{"sdp":"test"}}',
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 201)
        self.client.force_login(self.lamia)
        incoming = self.client.get(reverse('communications:incoming_call')).json()['call']
        self.assertEqual(incoming['caller'], 'sara')
        self.assertEqual(incoming['room_url'], room)
        self.assertContains(self.client.get(reverse('exchanges:requests')), room)
        polled = self.client.get(messages_url, {'after': 0}).json()['messages']
        self.assertEqual(polled[0]['content'], 'Hello Lamia')
        response = self.client.post(
            messages_url, data='{"content":"Welcome Sara"}', content_type='application/json',
        )
        self.assertEqual(response.status_code, 201)
        signals = self.client.get(signals_url).json()
        self.assertEqual(len(signals['signals']), 1)
        self.assertTrue(signals['ice_servers'])
        self.client.force_login(self.sara)
        replies = self.client.get(messages_url, {'after': first_message_id}).json()['messages']
        self.assertEqual(replies[0]['content'], 'Welcome Sara')
        self.client.force_login(self.lamia)
        self.assertEqual(self.client.post(
            signals_url, data='{"type":"answer","payload":{"sdp":"answer"}}',
            content_type='application/json',
        ).status_code, 201)
        self.client.force_login(self.outsider)
        self.assertIsNone(self.client.get(reverse('communications:incoming_call')).json()['call'])

    def test_room_javascript_requests_media_only_on_call_and_stops_tracks(self):
        script_path = finders.find('js/session-room.js')
        self.assertIsNotNone(script_path)
        with open(script_path, encoding='utf-8') as script_file:
            source = script_file.read()
        self.assertIn("addEventListener('click',()=>startCall(true))", source)
        self.assertIn('navigator.mediaDevices.getUserMedia', source)
        self.assertIn('new RTCPeerConnection', source)
        self.assertIn('localStream.getTracks().forEach(track=>track.stop())', source)
        self.assertIn('seenMessageIds', source)
        self.assertIn('sendButton.disabled=true', source)

    def test_call_event_has_one_record_and_server_calculated_duration(self):
        exchange = self.make_request()
        accept_exchange_request(exchange_id=exchange.pk, provider=self.lamia)
        session = exchange.sessions.get()
        signals_url = reverse('exchanges:room_signals', args=[session.pk])
        messages_url = reverse('exchanges:room_messages', args=[session.pk])
        call_client_id = str(uuid.uuid4())
        offer = '{"type":"offer","payload":{"media":"audio","client_call_id":"%s"}}' % call_client_id
        self.client.force_login(self.lamia)
        first = self.client.post(signals_url, data=offer, content_type='application/json')
        second = self.client.post(signals_url, data=offer, content_type='application/json')
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 201)
        self.assertEqual(CallEvent.objects.filter(client_id=call_client_id).count(), 1)
        call = CallEvent.objects.get(client_id=call_client_id)
        self.client.force_login(self.sara)
        answer = '{"type":"answer","payload":{"call_id":%s}}' % call.pk
        self.client.post(signals_url, data=answer, content_type='application/json')
        call.refresh_from_db()
        self.assertEqual(call.status, 'answered')
        call.answered_at = timezone.now() - timedelta(seconds=252)
        call.save(update_fields=['answered_at'])
        self.client.force_login(self.lamia)
        hangup = '{"type":"hangup","payload":{"call_id":%s}}' % call.pk
        self.client.post(signals_url, data=hangup, content_type='application/json')
        call.refresh_from_db()
        self.assertEqual(call.status, 'ended')
        self.assertGreaterEqual(call.duration_seconds, 252)
        timeline = self.client.get(messages_url).json()['call_events']
        self.assertEqual(len(timeline), 1)
        self.assertEqual(timeline[0]['status'], 'ended')

    def test_missed_call_is_unread_until_recipient_opens_room(self):
        exchange = self.make_request()
        accept_exchange_request(exchange_id=exchange.pk, provider=self.lamia)
        session = exchange.sessions.get()
        signals_url = reverse('exchanges:room_signals', args=[session.pk])
        room_url = reverse('exchanges:session_room', args=[session.pk])
        self.client.force_login(self.sara)
        response = self.client.post(
            signals_url,
            data='{"type":"offer","payload":{"media":"video","client_call_id":"%s"}}' % uuid.uuid4(),
            content_type='application/json',
        )
        call_id = response.json()['call_event']['id']
        self.client.post(
            signals_url, data='{"type":"hangup","payload":{"call_id":%s,"reason":"missed"}}' % call_id,
            content_type='application/json',
        )
        self.client.force_login(self.lamia)
        response = self.client.get(reverse('communications:conversation_list'))
        self.assertEqual(response.context['unread_messages_count'], 1)
        self.assertEqual(response.context['memberships'][0].unread_count, 1)
        self.client.get(room_url)
        response = self.client.get(reverse('communications:conversation_list'))
        self.assertEqual(response.context['unread_messages_count'], 0)

    def test_call_can_be_declined_or_cancelled_before_answer(self):
        exchange = self.make_request()
        accept_exchange_request(exchange_id=exchange.pk, provider=self.lamia)
        session = exchange.sessions.get()
        url = reverse('exchanges:room_signals', args=[session.pk])
        self.client.force_login(self.sara)
        response = self.client.post(url, data='{"type":"offer","payload":{"media":"audio","client_call_id":"%s"}}' % uuid.uuid4(), content_type='application/json')
        declined_id = response.json()['call_event']['id']
        self.client.force_login(self.lamia)
        self.client.post(url, data='{"type":"hangup","payload":{"call_id":%s,"reason":"declined"}}' % declined_id, content_type='application/json')
        self.assertEqual(CallEvent.objects.get(pk=declined_id).status, 'declined')
        self.client.force_login(self.sara)
        response = self.client.post(url, data='{"type":"offer","payload":{"media":"video","client_call_id":"%s"}}' % uuid.uuid4(), content_type='application/json')
        cancelled_id = response.json()['call_event']['id']
        self.client.post(url, data='{"type":"hangup","payload":{"call_id":%s}}' % cancelled_id, content_type='application/json')
        self.assertEqual(CallEvent.objects.get(pk=cancelled_id).status, 'cancelled')

    def test_message_idempotency_unread_badge_and_read_receipt(self):
        exchange = self.make_request()
        accept_exchange_request(exchange_id=exchange.pk, provider=self.lamia)
        session = exchange.sessions.get()
        messages_url = reverse('exchanges:room_messages', args=[session.pk])
        client_id = str(uuid.uuid4())
        self.client.force_login(self.sara)
        payload = '{"content":"One message only","client_id":"%s"}' % client_id
        first = self.client.post(messages_url, data=payload, content_type='application/json')
        second = self.client.post(messages_url, data=payload, content_type='application/json')
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.json()['message']['id'], second.json()['message']['id'])
        self.assertEqual(Message.objects.filter(content='One message only').count(), 1)
        self.assertEqual(Notification.objects.filter(user=self.lamia, notification_type='message').count(), 1)

        self.client.force_login(self.lamia)
        list_url = reverse('communications:conversation_list')
        response = self.client.get(list_url)
        self.assertContains(response, 'One message only')
        self.assertContains(response, 'hb-unread-badge')
        self.assertEqual(response.context['unread_messages_count'], 1)
        membership = ConversationParticipant.objects.get(
            conversation=exchange.conversation, user=self.lamia,
        )
        self.assertIsNone(membership.last_read_at)
        self.client.get(reverse('exchanges:session_room', args=[session.pk]))
        membership.refresh_from_db()
        self.assertIsNotNone(membership.last_read_at)
        response = self.client.get(list_url)
        self.assertEqual(response.context['unread_messages_count'], 0)

    def test_ten_messages_are_returned_once_each_and_hidden_from_outsider(self):
        exchange = self.make_request()
        accept_exchange_request(exchange_id=exchange.pk, provider=self.lamia)
        session = exchange.sessions.get()
        messages_url = reverse('exchanges:room_messages', args=[session.pk])
        self.client.force_login(self.sara)
        for index in range(10):
            response = self.client.post(
                messages_url,
                data='{"content":"Message %s","client_id":"%s"}' % (index, uuid.uuid4()),
                content_type='application/json',
            )
            self.assertEqual(response.status_code, 201)
        messages = self.client.get(messages_url, {'after': 0}).json()['messages']
        self.assertEqual(len(messages), 10)
        self.assertEqual(len({item['id'] for item in messages}), 10)
        self.client.force_login(self.outsider)
        response = self.client.get(reverse('communications:conversation_list'))
        self.assertNotContains(response, 'Message 9')

    def test_conversation_list_orders_by_latest_message(self):
        first_exchange = self.make_request()
        accept_exchange_request(exchange_id=first_exchange.pk, provider=self.lamia)
        outsider_skill = Skill.objects.create(
            category=self.python_offer.skill.category, name='Design'
        )
        outsider_offer = SkillOffer.objects.create(
            user=self.outsider, skill=outsider_skill, title='Learn Design',
            description='Design', hour_cost=1,
        )
        second_exchange = ExchangeRequest.objects.create(
            requester=self.lamia, provider=self.outsider, offer=outsider_offer,
            requested_hours=1,
        )
        accept_exchange_request(exchange_id=second_exchange.pk, provider=self.outsider)
        Message.objects.create(
            conversation=first_exchange.conversation, sender=self.sara, content='Older preview'
        )
        Message.objects.create(
            conversation=second_exchange.conversation, sender=self.outsider, content='Newest preview'
        )
        self.client.force_login(self.lamia)
        content = self.client.get(reverse('communications:conversation_list')).content.decode()
        self.assertLess(content.index('Newest preview'), content.index('Older preview'))
