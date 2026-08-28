from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.contrib import messages
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.utils.translation import get_language
from exchanges.models import ExchangeRequest

from .categories import CATEGORY_ALIASES, CATEGORY_EN
from .forms import ExchangeRequestForm, SkillOfferForm
from .models import Skill, SkillCategory, SkillOffer


def explore(request):
    offers = SkillOffer.objects.filter(is_active=True).select_related(
        'user',
        'user__profile',
        'skill',
        'skill__category',
    )

    search = request.GET.get('search', '').strip()
    category = request.GET.get('category', '').strip()
    level = request.GET.get('level', '').strip()
    delivery = request.GET.get('delivery', '').strip()
    duration = request.GET.get('duration', '').strip()
    sort = request.GET.get('sort', '').strip() or 'newest'

    if search:
        category_alias = next(
            (arabic for alias, arabic in CATEGORY_ALIASES.items() if search.casefold() in alias),
            None,
        )
        offers = offers.filter(
            Q(title__icontains=search)
            | Q(skill__name__icontains=search)
            | Q(description__icontains=search)
            | Q(skill__category__name__icontains=search)
            | Q(user__username__icontains=search)
            | (Q(skill__category__name=category_alias) if category_alias else Q())
        )

    if category:
        offers = offers.filter(skill__category_id=category)

    if level:
        offers = offers.filter(level=level)

    if delivery:
        offers = offers.filter(delivery_method=delivery)

    if duration:
        offers = offers.filter(session_duration_minutes=duration)

    ordering = {
        'newest': '-created_at',
        'rating': '-user__profile__average_rating',
        'hours': 'hour_cost',
    }
    if sort == 'popular':
        offers = offers.annotate(
            demand_count=Count('exchange_requests')
        ).order_by('-demand_count', '-created_at')
    else:
        offers = offers.order_by(ordering.get(sort, '-created_at'))

    categories = list(SkillCategory.objects.filter(is_active=True))
    language = get_language()
    for item in categories:
        item.localized_name = CATEGORY_EN.get(item.name, item.name) if language == 'en' else item.name
    offers = list(offers)
    for offer in offers:
        offer.category_label = CATEGORY_EN.get(offer.skill.category.name, offer.skill.category.name) if language == 'en' else offer.skill.category.name
    context = {
        'offers': offers,
        'categories': categories,
        'levels': SkillOffer.LEVEL_CHOICES,
        'delivery_methods': SkillOffer.DELIVERY_CHOICES,
        'durations': (30, 60, 90, 120),
        'filters': {
            'search': search,
            'category': category,
            'level': level,
            'delivery': delivery,
            'duration': duration,
            'sort': sort,
        },
    }
    return render(request, 'skills-templates/explore.html', context)


def offer_detail(request, pk):
    offer = get_object_or_404(
        SkillOffer.objects.select_related(
            'user',
            'user__profile',
            'skill',
            'skill__category',
        ),
        pk=pk,
    )
    if (not offer.is_active or not offer.skill.is_active) and offer.user_id != request.user.id:
        raise Http404
    return render(
        request,
        'skills-templates/offer_detail.html',
        {'offer': offer},
    )


@login_required(login_url='accounts:login')
def request_session(request, pk):
    offer = get_object_or_404(SkillOffer, pk=pk, is_active=True)
    if offer.user_id == request.user.id:
        messages.error(request, 'لا يمكنك طلب جلسة من عرضك الشخصي.')
        return redirect('skills:offer_detail', pk=pk)
    if ExchangeRequest.objects.filter(requester=request.user, offer=offer, status='pending').exists():
        messages.warning(request, 'You already have a pending request for this offer.')
        return redirect('skills:offer_detail', pk=pk)
    form = ExchangeRequestForm(request.POST or None, user=request.user)
    if request.method == 'POST' and form.is_valid():
        exchange = form.save(commit=False)
        exchange.requester = request.user
        exchange.provider = offer.user
        exchange.offer = offer
        exchange.requested_hours = offer.hour_cost
        exchange.save()
        messages.success(request, 'تم إرسال طلب الجلسة بنجاح.')
        return redirect('skills:offer_detail', pk=pk)
    return render(
        request,
        'skills-templates/request_session.html',
        {'offer': offer, 'form': form},
    )


@login_required(login_url='accounts:login')
def my_skills(request):
    offers = SkillOffer.objects.filter(user=request.user).select_related(
        'skill', 'skill__category'
    )
    return render(request, 'skills-templates/my_skills.html', {'offers': offers})


@login_required(login_url='accounts:login')
def create_offer(request):
    form = SkillOfferForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        offer = form.save(commit=False)
        offer.user = request.user
        offer.skill = form.resolve_skill()
        offer.save()
        messages.success(request, 'تم إنشاء عرض المهارة بنجاح.')
        return redirect('skills:my_skills')
    return render(request, 'skills-templates/create_offer.html', {
        'form': form, 'skill_suggestions': Skill.objects.filter(is_active=True).order_by('name'),
    })


@login_required(login_url='accounts:login')
def offer_edit(request, pk):
    offer = get_object_or_404(SkillOffer, pk=pk, user=request.user)
    form = SkillOfferForm(request.POST or None, instance=offer)
    if request.method == 'POST' and form.is_valid():
        offer = form.save(commit=False)
        offer.skill = form.resolve_skill()
        offer.save()
        messages.success(request, 'تم تحديث عرض المهارة بنجاح.')
        return redirect('skills:my_skills')
    return render(request, 'skills-templates/edit_offer.html', {
        'form': form, 'offer': offer,
        'skill_suggestions': Skill.objects.filter(is_active=True).order_by('name'),
    })


@login_required(login_url='accounts:login')
def offer_delete(request, pk):
    offer = get_object_or_404(SkillOffer, pk=pk, user=request.user)
    if request.method == 'POST':
        offer.delete()
        messages.success(request, 'تم حذف عرض المهارة.')
        return redirect('skills:my_skills')
    return render(request, 'skills-templates/delete_offer.html', {'offer': offer})


@login_required(login_url='accounts:login')
@require_POST
def offer_toggle(request, pk):
    offer = get_object_or_404(SkillOffer, pk=pk, user=request.user)
    offer.is_active = not offer.is_active
    offer.save(update_fields=['is_active', 'updated_at'])
    messages.success(request, 'تم تغيير حالة العرض بنجاح.')
    return redirect('skills:my_skills')
