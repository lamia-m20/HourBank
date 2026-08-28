from django import forms
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.utils import timezone
from django.utils.translation import get_language, gettext_lazy as _

from exchanges.models import ExchangeRequest

from .categories import CATEGORY_EN
from .models import Skill, SkillCategory, SkillOffer


class CategoryChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return CATEGORY_EN.get(obj.name, obj.name) if get_language() == 'en' else obj.name


class SkillOfferForm(forms.ModelForm):
    category = CategoryChoiceField(
        label=_('Category'), queryset=SkillCategory.objects.none(), required=True
    )
    skill_name = forms.CharField(
        label=_('Skill name'), max_length=150, required=True,
        widget=forms.TextInput(attrs={
            'autocomplete': 'off', 'list': 'skill-suggestions',
            'placeholder': _('Example: Python or graphic design'),
        }),
    )

    class Meta:
        model = SkillOffer
        fields = (
            'title', 'description', 'level', 'delivery_method',
            'session_duration_minutes', 'hour_cost', 'is_active',
        )
        labels = {
            'title': _('Offer title'), 'description': _('Offer description'),
            'level': _('Level'), 'delivery_method': _('Delivery method'),
            'session_duration_minutes': _('Session duration in minutes'),
            'hour_cost': _('Session cost in hours'), 'is_active': _('Offer is active'),
        }
        widgets = {'description': forms.Textarea(attrs={'rows': 5})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].queryset = SkillCategory.objects.filter(is_active=True)
        if self.instance and self.instance.pk:
            self.fields['category'].initial = self.instance.skill.category
            self.fields['skill_name'].initial = self.instance.skill.name
        for field in self.fields.values():
            if not isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.setdefault('class', 'form-control')

    def clean_skill_name(self):
        name = self.cleaned_data['skill_name'].strip()
        if not name:
            raise forms.ValidationError(_('Skill name is required.'))
        return name

    def resolve_skill(self):
        category = self.cleaned_data['category']
        skill_name = self.cleaned_data['skill_name']
        skill = Skill.objects.filter(category=category, name__iexact=skill_name).first()
        return skill or Skill.objects.create(category=category, name=skill_name, is_active=True)

    def clean_session_duration_minutes(self):
        duration = self.cleaned_data['session_duration_minutes']
        if duration < 15 or duration > 480:
            raise forms.ValidationError(_('Session duration must be between 15 and 480 minutes.'))
        return duration

    def clean_hour_cost(self):
        cost = self.cleaned_data['hour_cost']
        if cost <= 0:
            raise forms.ValidationError(_('Session cost must be greater than zero.'))
        return cost


class ExchangeRequestForm(forms.ModelForm):
    class Meta:
        model = ExchangeRequest
        fields = ('requested_date', 'requested_time', 'message')
        labels = {
            'requested_date': _('Session start date'),
            'requested_time': _('Session start time'),
            'message': _('Message to the provider'),
        }
        widgets = {
            'requested_date': forms.DateInput(attrs={'type': 'date'}),
            'requested_time': forms.TimeInput(attrs={'type': 'time'}),
            'message': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.fields['requested_date'].required = True
        self.fields['requested_time'].required = True
        self.fields['requested_date'].widget.attrs['min'] = self._local_now().date().isoformat()
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control')

    def _timezone(self):
        timezone_name = getattr(getattr(self.user, 'profile', None), 'timezone', None)
        if timezone_name:
            try:
                return ZoneInfo(timezone_name)
            except ZoneInfoNotFoundError:
                pass
        return timezone.get_current_timezone()

    def _local_now(self):
        return timezone.localtime(timezone.now(), self._timezone())

    def clean(self):
        cleaned_data = super().clean()
        requested_date = cleaned_data.get('requested_date')
        requested_time = cleaned_data.get('requested_time')
        if not requested_date or not requested_time:
            return cleaned_data

        local_now = self._local_now()
        if requested_date < local_now.date():
            self.add_error('requested_date', _('You cannot select a past date.'))
        elif requested_date == local_now.date():
            requested_at = timezone.make_aware(
                datetime.combine(requested_date, requested_time), self._timezone()
            )
            if requested_at <= local_now:
                self.add_error('requested_time', _('You cannot select a past time.'))
        return cleaned_data
