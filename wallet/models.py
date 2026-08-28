import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class HourWallet(models.Model):

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='hour_wallet',
        verbose_name='المستخدم'
    )

    available_balance = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=20,
        verbose_name='الرصيد المتاح'
    )

    held_balance = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='الرصيد المحجوز'
    )

    total_earned = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='إجمالي الساعات المكتسبة'
    )

    total_spent = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='إجمالي الساعات المستخدمة'
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='تاريخ الإنشاء'
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='آخر تحديث'
    )

    class Meta:
        verbose_name = 'محفظة ساعات'
        verbose_name_plural = 'محافظ الساعات'
        constraints = [
            models.CheckConstraint(condition=models.Q(available_balance__gte=0), name='wallet_available_nonnegative'),
            models.CheckConstraint(condition=models.Q(held_balance__gte=0), name='wallet_held_nonnegative'),
            models.CheckConstraint(condition=models.Q(total_earned__gte=0), name='wallet_earned_nonnegative'),
            models.CheckConstraint(condition=models.Q(total_spent__gte=0), name='wallet_spent_nonnegative'),
        ]

    def __str__(self):
        return f'محفظة {self.user}'


class HourTransaction(models.Model):

    TRANSACTION_TYPES = [
        ('welcome', _('Welcome bonus')), ('earned', _('Earned')),
        ('spent', _('Spent')), ('hold', _('Hold')), ('release', _('Release')),
        ('refund', _('Refund')), ('adjustment', _('Adjustment')), ('bonus', _('Bonus')),
    ]

    DIRECTION_CHOICES = [
        ('credit', _('Credit')), ('debit', _('Debit')),
    ]

    wallet = models.ForeignKey(
        HourWallet,
        on_delete=models.PROTECT,
        related_name='transactions',
        verbose_name='المحفظة'
    )

    exchange = models.ForeignKey(
        'exchanges.ExchangeRequest',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='wallet_transactions',
        verbose_name='طلب التبادل'
    )

    transaction_type = models.CharField(
        max_length=20,
        choices=TRANSACTION_TYPES,
        verbose_name='نوع العملية'
    )

    direction = models.CharField(
        max_length=10,
        choices=DIRECTION_CHOICES,
        verbose_name='اتجاه العملية'
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='عدد الساعات'
    )

    balance_after = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='الرصيد بعد العملية'
    )

    reference = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        verbose_name='رقم المرجع'
    )

    description = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='وصف العملية'
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='تاريخ العملية'
    )

    class Meta:
        verbose_name = 'حركة ساعات'
        verbose_name_plural = 'حركات الساعات'
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['wallet', 'exchange', 'transaction_type'],
                condition=models.Q(
                    exchange__isnull=False,
                    transaction_type__in=['hold', 'release', 'spent', 'earned'],
                ),
                name='unique_wallet_exchange_lifecycle_transaction',
            )
        ]

    def __str__(self):
        return f'{self.wallet.user} - {self.amount} ساعة'


class HourHold(models.Model):

    STATUS_CHOICES = [
        ('active', _('Active')), ('captured', _('Captured')),
        ('released', _('Released')), ('cancelled', _('Cancelled')),
    ]

    wallet = models.ForeignKey(
        HourWallet,
        on_delete=models.PROTECT,
        related_name='holds',
        verbose_name='المحفظة'
    )

    exchange = models.ForeignKey(
        'exchanges.ExchangeRequest',
        on_delete=models.PROTECT,
        related_name='hour_holds',
        verbose_name='طلب التبادل'
    )

    payee = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name='incoming_hour_holds', verbose_name=_('Hour recipient'), null=True, blank=True,
    )

    offer = models.ForeignKey(
        'skills.SkillOffer', on_delete=models.PROTECT,
        related_name='hour_holds', verbose_name=_('Skill offer'), null=True, blank=True,
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='الساعات المحجوزة'
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active',
        verbose_name='حالة الحجز'
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='وقت الحجز'
    )

    released_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='وقت فك الحجز'
    )

    class Meta:
        verbose_name = 'حجز ساعات'
        verbose_name_plural = 'حجوزات الساعات'
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['exchange', 'wallet', 'payee', 'offer'], name='unique_exchange_direction_hold'
            )
        ]

    def __str__(self):
        return f'{self.wallet.user} - {self.amount} ساعة'
