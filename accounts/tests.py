from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase
from django.test import override_settings
from django.urls import reverse
from django.core import mail

from wallet.models import HourWallet

from .models import UserProfile


class ProfileViewsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('member', 'member@example.com', 'pass12345')
        UserProfile.objects.create(user=self.user, city='Riyadh', birth_date=date(2000, 9, 1))

    def test_private_profile_requires_login_and_creates_wallet(self):
        response = self.client.get(reverse('accounts:profile'))
        self.assertEqual(response.status_code, 302)
        self.client.force_login(self.user)
        response = self.client.get(reverse('accounts:profile'))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(HourWallet.objects.filter(user=self.user).exists())

    def test_profile_edit_updates_user_and_profile(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse('accounts:profile_edit'), {
            'first_name': 'محمد', 'last_name': 'أحمد', 'bio': 'نبذة',
            'birth_date': '2000-09-01', 'city': 'Riyadh', 'country': 'SA',
            'timezone': 'Asia/Riyadh', 'preferred_language': 'ar',
            'is_available': 'on',
        })
        self.assertRedirects(response, reverse('accounts:profile'))
        self.user.refresh_from_db()
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.first_name, 'محمد')
        self.assertEqual(self.user.profile.city, 'Riyadh')

    def test_public_profile_hides_private_fields(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('accounts:public_profile', args=[self.user.username]))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, self.user.email)
        self.assertNotContains(response, '2000-09-01')
        self.assertNotContains(response, 'محفظة الساعات')

    def test_registration_and_login_still_work_after_profile_change(self):
        response = self.client.post(reverse('accounts:register'), {
            'username': 'new_member', 'email': 'new@example.com',
            'password1': 'safe-pass-123', 'password2': 'safe-pass-123',
            'account_type': 'individual', 'city': 'Riyadh', 'country': 'SA',
            'birth_date': '2000-01-01',
        })
        self.assertEqual(response.status_code, 302)
        self.client.logout()
        response = self.client.post(reverse('accounts:login'), {
            'username': 'new_member', 'password': 'safe-pass-123',
        })
        self.assertEqual(response.status_code, 302)

    def test_registration_rejects_future_birth_date(self):
        self.client.cookies['django_language'] = 'en'
        response = self.client.post(reverse('accounts:register'), {
            'username': 'future_member', 'email': 'future@example.com',
            'password1': 'safe-pass-123', 'password2': 'safe-pass-123',
            'birth_date': '2999-01-01',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username='future_member').exists())
        self.assertContains(response, 'Date of birth cannot be in the future.')

    def test_age_is_calculated_accurately_and_missing_date_returns_none(self):
        today = date.today()
        expected = today.year - 2000 - ((today.month, today.day) < (9, 1))
        self.assertEqual(self.user.profile.age, expected)
        self.user.profile.birth_date = None
        self.assertIsNone(self.user.profile.age)

    def test_dashboard_wallet_journey_sessions_and_requests_open(self):
        self.client.force_login(self.user)
        urls = (
            reverse('accounts:dashboard'), reverse('wallet:detail'),
            reverse('accounts:learning_journey'), reverse('exchanges:sessions'),
            reverse('exchanges:requests'),
        )
        for url in urls:
            self.assertEqual(self.client.get(url).status_code, 200)

    def test_homepage_and_language_switch_open_without_phone_feature(self):
        self.assertEqual(self.client.get('/').status_code, 200)
        response = self.client.post(reverse('set_language'), {
            'language': 'en', 'next': reverse('accounts:dashboard'),
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.cookies['django_language'].value, 'en')

    def test_language_switch_translates_page_direction_and_updates_profile(self):
        self.client.force_login(self.user)
        self.client.post(reverse('set_language'), {
            'language': 'en', 'next': reverse('accounts:dashboard'),
        })
        response = self.client.get(reverse('accounts:dashboard'))
        self.assertContains(response, 'lang="en"')
        self.assertContains(response, 'dir="ltr"')
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.preferred_language, 'en')
        self.client.post(reverse('set_language'), {
            'language': 'ar', 'next': reverse('accounts:dashboard'),
        })
        response = self.client.get(reverse('accounts:dashboard'))
        self.assertContains(response, 'lang="ar"')
        self.assertContains(response, 'dir="rtl"')

    def test_shared_header_styles_load_on_required_pages_in_both_languages(self):
        self.client.force_login(self.user)
        pages = (
            '/', reverse('skills:explore'), reverse('skills:create_offer'),
            reverse('skills:my_skills'), reverse('accounts:profile'),
            reverse('accounts:dashboard'),
        )
        for language, direction in (('ar', 'rtl'), ('en', 'ltr')):
            self.client.post(reverse('set_language'), {'language': language, 'next': '/'})
            for url in pages:
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'css/site-chrome.css')
                self.assertContains(response, 'class="hb-sidebar"')
                self.assertContains(response, 'aria-hidden="true"')
                self.assertContains(response, f'dir="{direction}"')


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class PasswordResetTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            'reset_member', 'reset@example.com', 'old-safe-password-123'
        )

    def test_invalid_login_uses_generic_message(self):
        self.client.cookies['django_language'] = 'en'
        response = self.client.post(reverse('accounts:login'), {
            'username': self.user.username, 'password': 'wrong-password',
        })
        self.assertContains(response, 'Invalid username or password.')
        self.assertContains(response, 'class="login-error"')

    def test_unknown_email_shows_same_generic_done_page_without_email(self):
        response = self.client.post(reverse('accounts:password_reset'), {
            'email': 'unknown@example.com',
        }, follow=True)
        self.assertContains(response, 'إذا كان هذا البريد مرتبطاً بحساب')
        self.assertEqual(len(mail.outbox), 0)

    def test_password_reset_changes_password_and_invalidates_token(self):
        response = self.client.post(reverse('accounts:password_reset'), {
            'email': self.user.email,
        })
        self.assertRedirects(response, reverse('accounts:password_reset_done'))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('إعادة تعيين كلمة المرور - HourBank', mail.outbox[0].subject)
        reset_url = next(
            line for line in mail.outbox[0].body.splitlines()
            if '/accounts/reset/' in line
        )
        response = self.client.get(reset_url)
        self.assertEqual(response.status_code, 302)
        confirm_url = response.url
        response = self.client.post(confirm_url, {
            'new_password1': 'new-safe-password-456',
            'new_password2': 'new-safe-password-456',
        })
        self.assertRedirects(response, reverse('accounts:password_reset_complete'))
        self.user.refresh_from_db()
        self.assertFalse(self.user.check_password('old-safe-password-123'))
        self.assertTrue(self.user.check_password('new-safe-password-456'))
        self.assertFalse(self.client.login(
            username=self.user.username, password='old-safe-password-123'
        ))
        self.assertTrue(self.client.login(
            username=self.user.username, password='new-safe-password-456'
        ))
