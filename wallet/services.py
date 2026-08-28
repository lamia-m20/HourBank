from decimal import Decimal

from django.db import transaction

from .models import HourTransaction, HourWallet


WELCOME_HOURS = Decimal('20.00')


@transaction.atomic
def ensure_welcome_credit(user):
    wallet, created = HourWallet.objects.select_for_update().get_or_create(
        user=user, defaults={'available_balance': WELCOME_HOURS}
    )
    if HourTransaction.objects.filter(wallet=wallet, transaction_type='welcome').exists():
        return wallet
    if not created:
        wallet.available_balance += WELCOME_HOURS
        wallet.save(update_fields=['available_balance', 'updated_at'])
    HourTransaction.objects.create(
        wallet=wallet, transaction_type='welcome', direction='credit',
        amount=WELCOME_HOURS, balance_after=wallet.available_balance,
        description='Initial HourBank credit',
    )
    return wallet
