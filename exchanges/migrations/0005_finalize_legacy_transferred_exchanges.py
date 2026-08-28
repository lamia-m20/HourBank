from django.db import migrations


def finalize_legacy_transferred_exchanges(apps, schema_editor):
    ExchangeRequest = apps.get_model('exchanges', 'ExchangeRequest')
    legacy_ids = ExchangeRequest.objects.filter(
        status='accepted', wallet_transactions__transaction_type='earned'
    ).values_list('pk', flat=True).distinct()
    ExchangeRequest.objects.filter(pk__in=legacy_ids).update(status='completed')


class Migration(migrations.Migration):
    dependencies = [
        ('exchanges', '0004_exchangerequest_reverse_offer_session_learner_and_more'),
        ('wallet', '0004_hourhold_offer_hourhold_payee_and_more'),
    ]

    operations = [
        migrations.RunPython(finalize_legacy_transferred_exchanges, migrations.RunPython.noop),
    ]
