from .models import ExchangeRequest


def unseen_exchange_requests(request):
    if not request.user.is_authenticated:
        return {'pending_exchange_requests_count': 0}
    if request.resolver_match and request.resolver_match.view_name == 'exchanges:requests':
        return {'pending_exchange_requests_count': 0}
    count = ExchangeRequest.objects.filter(
        offer__user=request.user,
        status='pending',
        provider_seen_at__isnull=True,
    ).count()
    return {'pending_exchange_requests_count': count}
