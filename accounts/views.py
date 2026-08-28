from django.contrib import messages
from django.contrib.auth import (
    authenticate,
    login,
    logout,
)
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.views.i18n import set_language as django_set_language
from django.db.models import Q
from django.shortcuts import get_object_or_404, render, redirect
from django.utils.translation import gettext as _

from skills.models import SkillOffer
from wallet.models import HourWallet
from exchanges.models import ExchangeRequest, Session

from .forms import RegistrationBirthDateForm, UserProfileForm
from .models import UserProfile


def register_view(request):
    """
    إنشاء حساب مستخدم جديد.
    """

    if request.user.is_authenticated:
        return redirect('/')

    birth_date_form = RegistrationBirthDateForm(request.POST or None)

    if request.method == 'POST':

        username = request.POST.get(
            'username',
            ''
        ).strip()

        email = request.POST.get(
            'email',
            ''
        ).strip().lower()

        password1 = request.POST.get(
            'password1',
            ''
        )

        password2 = request.POST.get(
            'password2',
            ''
        )

        account_type = request.POST.get(
            'account_type',
            'individual'
        )

        city = request.POST.get(
            'city',
            ''
        ).strip()

        country = request.POST.get(
            'country',
            ''
        ).strip()

        birth_date_is_valid = birth_date_form.is_valid()

        if (
            not username
            or not email
            or not password1
            or not password2
            or not birth_date_is_valid
        ):
            messages.error(
                request,
                'يرجى تعبئة جميع الحقول المطلوبة.'
            )

            return render(
                request,
                'accounts-templates/register.html',
                {'birth_date_form': birth_date_form},
            )

        if password1 != password2:

            messages.error(
                request,
                'كلمتا المرور غير متطابقتين.'
            )

            return render(
                request,
                'accounts-templates/register.html',
                {'birth_date_form': birth_date_form},
            )

        if User.objects.filter(
            username=username
        ).exists():

            messages.error(
                request,
                'اسم المستخدم مستخدم بالفعل.'
            )

            return render(
                request,
                'accounts-templates/register.html',
                {'birth_date_form': birth_date_form},
            )

        if User.objects.filter(
            email__iexact=email
        ).exists():

            messages.error(
                request,
                'البريد الإلكتروني مستخدم بالفعل.'
            )

            return render(
                request,
                'accounts-templates/register.html',
                {'birth_date_form': birth_date_form},
            )

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password1
        )

        UserProfile.objects.create(
            user=user,
            account_type=account_type,
            birth_date=birth_date_form.cleaned_data['birth_date'],
            city=city,
            country=country
        )

        login(
            request,
            user
        )

        messages.success(
            request,
            'تم إنشاء الحساب بنجاح.'
        )

        return redirect('/')

    return render(
        request,
        'accounts-templates/register.html',
        {'birth_date_form': birth_date_form},
    )


def login_view(request):
    """
    تسجيل الدخول.
    """

    if request.user.is_authenticated:
        return redirect('/')

    if request.method == 'POST':

        username = request.POST.get(
            'username',
            ''
        ).strip()

        password = request.POST.get(
            'password',
            ''
        )

        if not username or not password:

            messages.error(
                request,
                'يرجى إدخال اسم المستخدم وكلمة المرور.'
            )

            return render(
                request,
                'accounts-templates/login.html'
            )

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user is not None:

            login(
                request,
                user
            )

            messages.success(
                request,
                'تم تسجيل الدخول بنجاح.'
            )

            next_url = request.GET.get(
                'next'
            )

            if next_url:
                return redirect(next_url)

            return redirect('/')

        messages.error(
            request,
            _('Invalid username or password.')
        )

    return render(
        request,
        'accounts-templates/login.html'
    )


def logout_view(request):
    """
    تسجيل الخروج.
    """

    logout(request)

    messages.success(
        request,
        'تم تسجيل الخروج بنجاح.'
    )

    return redirect('/')


@login_required(login_url='accounts:login')
def profile_view(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    wallet, _ = HourWallet.objects.get_or_create(user=request.user)
    offers_count = SkillOffer.objects.filter(user=request.user).count()
    return render(request, 'accounts-templates/profile.html', {
        'profile': profile, 'wallet': wallet, 'offers_count': offers_count,
    })


@login_required(login_url='accounts:login')
def profile_edit(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    form = UserProfileForm(
        request.POST or None, request.FILES or None, instance=profile, user=request.user
    )
    if request.method == 'POST' and form.is_valid():
        saved_profile = form.save()
        request.session['django_language'] = saved_profile.preferred_language
        messages.success(request, 'تم تحديث ملفك الشخصي بنجاح.')
        return redirect('accounts:profile')
    return render(request, 'accounts-templates/profile_edit.html', {'form': form})


@login_required(login_url='accounts:login')
def public_profile(request, username):
    profile_user = get_object_or_404(User, username=username)
    profile, _ = UserProfile.objects.get_or_create(user=profile_user)
    offers = SkillOffer.objects.filter(
        user=profile_user, is_active=True, skill__is_active=True
    ).select_related('skill', 'skill__category')
    return render(request, 'accounts-templates/public_profile.html', {
        'profile_user': profile_user, 'profile': profile, 'offers': offers,
    })


@login_required(login_url='accounts:login')
def dashboard(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    wallet, _ = HourWallet.objects.get_or_create(user=request.user)
    exchanges = ExchangeRequest.objects.filter(
        Q(requester=request.user) | Q(provider=request.user)
    ).select_related('offer', 'requester', 'provider')
    return render(request, 'accounts-templates/dashboard.html', {
        'profile': profile, 'wallet': wallet,
        'offers_count': SkillOffer.objects.filter(user=request.user).count(),
        'requests_count': exchanges.count(),
        'sessions_count': Session.objects.filter(
            Q(exchange__requester=request.user) | Q(exchange__provider=request.user)
        ).count(),
        'recent_exchanges': exchanges[:5],
    })


@login_required(login_url='accounts:login')
def learning_journey(request):
    completed = Session.objects.filter(
        status='completed', completed_at__isnull=False,
    ).exclude(disputes__isnull=False).exclude(
        confirmations__issue_reported=True,
    ).select_related(
        'offer__skill', 'learner__profile', 'provider__profile',
    ).distinct().order_by('-completed_at', '-pk')
    return render(request, 'accounts-templates/learning_journey.html', {
        'learned': completed.filter(learner=request.user),
        'taught': completed.filter(provider=request.user),
    })


def set_language(request):
    response = django_set_language(request)
    language = request.POST.get('language')
    if request.user.is_authenticated and language in dict(settings.LANGUAGES):
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        if profile.preferred_language != language:
            profile.preferred_language = language
            profile.save(update_fields=['preferred_language', 'updated_at'])
    return response
