from datetime import date, datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils.translation import override

from accounts.models import UserProfile
from exchanges.models import ExchangeRequest

from .forms import ExchangeRequestForm

from .categories import CATEGORY_NAMES
from .models import Skill, SkillCategory, SkillOffer


class SkillOfferViewsTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user('owner', password='pass12345')
        self.other = User.objects.create_user('other', password='pass12345')
        UserProfile.objects.create(user=self.owner, birth_date=date(1990, 1, 15))
        UserProfile.objects.create(user=self.other)
        category, _ = SkillCategory.objects.get_or_create(name=CATEGORY_NAMES[0][0])
        self.skill = Skill.objects.create(category=category, name='Python')
        self.offer = SkillOffer.objects.create(
            user=self.owner, skill=self.skill, title='تعلم Django',
            description='وصف العرض', hour_cost=1,
        )

    def test_create_assigns_authenticated_user(self):
        self.client.force_login(self.other)
        response = self.client.post(reverse('skills:create_offer'), {
            'category': self.skill.category_id, 'skill_name': 'Python',
            'title': 'New offer', 'description': 'Details',
            'level': 'beginner', 'delivery_method': 'online',
            'session_duration_minutes': 60, 'hour_cost': 1, 'is_active': 'on',
        })
        self.assertRedirects(response, reverse('skills:my_skills'))
        self.assertTrue(SkillOffer.objects.filter(user=self.other, title='New offer').exists())
        self.assertEqual(Skill.objects.filter(category=self.skill.category, name__iexact='Python').count(), 1)

    def test_other_user_cannot_edit_delete_or_toggle(self):
        self.client.force_login(self.other)
        for name in ('offer_edit', 'offer_delete', 'offer_toggle'):
            response = self.client.post(reverse(f'skills:{name}', args=[self.offer.pk]))
            self.assertEqual(response.status_code, 404)

    def test_toggle_is_post_only_and_hides_offer_from_explore(self):
        self.client.force_login(self.owner)
        url = reverse('skills:offer_toggle', args=[self.offer.pk])
        self.assertEqual(self.client.get(url).status_code, 405)
        self.client.post(url)
        self.offer.refresh_from_db()
        self.assertFalse(self.offer.is_active)
        self.assertNotContains(self.client.get(reverse('skills:explore')), self.offer.title)

    def test_user_can_create_new_skill_in_selected_category(self):
        self.client.force_login(self.other)
        response = self.client.post(reverse('skills:create_offer'), {
            'category': self.skill.category_id, 'skill_name': 'Django',
            'title': 'Django basics', 'description': 'Learn the basics',
            'level': 'beginner', 'delivery_method': 'in_person',
            'session_duration_minutes': 60, 'hour_cost': 1, 'is_active': 'on',
        })
        self.assertRedirects(response, reverse('skills:my_skills'))
        self.assertTrue(Skill.objects.filter(name='Django', category=self.skill.category).exists())

    def test_search_matches_skill_arabic_category_and_english_alias(self):
        for query in ('Python', CATEGORY_NAMES[0][0], 'Programming'):
            response = self.client.get(reverse('skills:explore'), {'search': query})
            self.assertContains(response, self.offer.title)

    @patch('skills.forms.timezone.now')
    def test_request_form_rejects_past_date_and_same_day_past_time(self, now_mock):
        now_mock.return_value = datetime(2026, 8, 26, 15, 30, tzinfo=ZoneInfo('UTC'))
        with override('en'):
            past_date = ExchangeRequestForm({
                'requested_date': '2026-08-25', 'requested_time': '20:00', 'message': '',
            }, user=self.other)
            self.assertFalse(past_date.is_valid())
            self.assertIn('You cannot select a past date.', past_date.errors['requested_date'])
            past_time = ExchangeRequestForm({
                'requested_date': '2026-08-26', 'requested_time': '18:00', 'message': '',
            }, user=self.other)
            self.assertFalse(past_time.is_valid())
            self.assertIn('You cannot select a past time.', past_time.errors['requested_time'])

    @patch('skills.forms.timezone.now')
    def test_future_request_uses_offer_cost_and_page_has_date_minimum(self, now_mock):
        now_mock.return_value = datetime(2026, 8, 26, 15, 30, tzinfo=ZoneInfo('UTC'))
        self.client.force_login(self.other)
        url = reverse('skills:request_session', args=[self.offer.pk])
        response = self.client.get(url)
        self.assertContains(response, 'min="2026-08-26"')
        response = self.client.post(url, {
            'requested_date': '2026-08-27', 'requested_time': '09:00', 'message': 'Please',
        })
        self.assertEqual(response.status_code, 302)
        exchange = ExchangeRequest.objects.get(requester=self.other, offer=self.offer)
        self.assertEqual(exchange.requested_hours, self.offer.hour_cost)

    def test_public_offer_shows_age_without_revealing_birth_date(self):
        response = self.client.get(reverse('skills:offer_detail', args=[self.offer.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, str(self.owner.profile.age))
        self.assertNotContains(response, '1990-01-15')
