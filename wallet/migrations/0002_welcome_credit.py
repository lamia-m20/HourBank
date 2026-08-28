from decimal import Decimal

from django.conf import settings
from django.db import migrations, models


def grant_welcome_credit(apps, schema_editor):
    User = apps.get_model(*settings.AUTH_USER_MODEL.split('.'))
    HourWallet = apps.get_model('wallet', 'HourWallet')
    HourTransaction = apps.get_model('wallet', 'HourTransaction')
    amount = Decimal('20.00')
    for user in User.objects.all().iterator():
        wallet, created = HourWallet.objects.get_or_create(
            user_id=user.pk, defaults={'available_balance': amount}
        )
        if HourTransaction.objects.filter(wallet_id=wallet.pk, transaction_type='welcome').exists():
            continue
        if not created:
            wallet.available_balance += amount
            wallet.save(update_fields=['available_balance'])
        HourTransaction.objects.create(
            wallet_id=wallet.pk, transaction_type='welcome', direction='credit',
            amount=amount, balance_after=wallet.available_balance,
            description='Initial HourBank credit',
        )


class Migration(migrations.Migration):
    dependencies = [('wallet', '0001_initial'), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.AlterField(
            model_name='hourwallet', name='available_balance',
            field=models.DecimalField(decimal_places=2, default=20, max_digits=10, verbose_name='available balance'),
        ),
        migrations.RunPython(grant_welcome_credit, migrations.RunPython.noop),
    ]
