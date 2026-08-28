from django import forms
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .models import UserProfile


COUNTRY_CHOICES = [
    ('', _('Choose country')), ('SA', _('Saudi Arabia')), ('AE', _('United Arab Emirates')),
    ('KW', _('Kuwait')), ('BH', _('Bahrain')), ('QA', _('Qatar')), ('OM', _('Oman')),
    ('EG', _('Egypt')), ('JO', _('Jordan')), ('OTHER', _('Other')),
]
REGION_CHOICES = [
    ('', _('Choose region')), ('Riyadh', _('Riyadh')), ('Makkah', _('Makkah')),
    ('Madinah', _('Madinah')), ('Eastern', _('Eastern Province')),
    ('Qassim', _('Qassim')), ('Asir', _('Asir')), ('Other', _('Other')),
]
TIMEZONE_CHOICES = [
    ('Asia/Riyadh', _('Riyadh (UTC+3)')), ('Asia/Dubai', _('Dubai (UTC+4)')),
    ('Asia/Kuwait', _('Kuwait (UTC+3)')), ('Africa/Cairo', _('Cairo (UTC+3)')),
    ('UTC', 'UTC'),
]
LANGUAGE_CHOICES = [('ar', _('Arabic')), ('en', _('English'))]


def validate_birth_date(value):
    if value and value > timezone.localdate():
        raise forms.ValidationError(_('Date of birth cannot be in the future.'))


class RegistrationBirthDateForm(forms.Form):
    birth_date = forms.DateField(
        label=_('Date of birth'),
        required=True,
        validators=[validate_birth_date],
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['birth_date'].widget.attrs['max'] = timezone.localdate().isoformat()


class UserProfileForm(forms.ModelForm):
    first_name = forms.CharField(label=_('First name'), max_length=150, required=False)
    last_name = forms.CharField(label=_('Last name'), max_length=150, required=False)

    class Meta:
        model = UserProfile
        fields = (
            'first_name', 'last_name', 'profile_image', 'bio',
            'birth_date', 'city', 'country', 'timezone', 'preferred_language', 'is_available',
        )
        labels = {
            'profile_image': _('Profile image'), 'bio': _('Bio'),
            'birth_date': _('Date of birth'),
            'city': _('Region'), 'country': _('Country'),
            'timezone': _('Time zone'), 'preferred_language': _('Preferred language'),
            'is_available': _('Available to teach'),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['country'].widget = forms.Select(choices=COUNTRY_CHOICES)
        self.fields['city'].widget = forms.Select(choices=REGION_CHOICES)
        self.fields['timezone'].widget = forms.Select(choices=TIMEZONE_CHOICES)
        self.fields['preferred_language'].widget = forms.Select(choices=LANGUAGE_CHOICES)
        self.fields['birth_date'].widget = forms.DateInput(attrs={
            'type': 'date', 'max': timezone.localdate().isoformat(),
        })
        self.user = user
        if user:
            self.fields['first_name'].initial = user.first_name
            self.fields['last_name'].initial = user.last_name
        for field in self.fields.values():
            if not isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.setdefault('class', 'form-control')

    def clean_birth_date(self):
        birth_date = self.cleaned_data.get('birth_date')
        validate_birth_date(birth_date)
        return birth_date

    def save(self, commit=True):
        profile = super().save(commit=False)
        if self.user:
            self.user.first_name = self.cleaned_data['first_name'].strip()
            self.user.last_name = self.cleaned_data['last_name'].strip()
            if commit:
                self.user.save(update_fields=['first_name', 'last_name'])
        if commit:
            profile.save()
        return profile
