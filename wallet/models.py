import uuid

from django.conf import settings
from django.db import models


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
        default=0,
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

    def __str__(self):
        return f'محفظة {self.user}'


class HourTransaction(models.Model):

    TRANSACTION_TYPES = [
        ('welcome', 'رصيد ترحيبي'),
        ('earned', 'ساعات مكتسبة'),
        ('spent', 'ساعات مستخدمة'),
        ('hold', 'حجز ساعات'),
        ('release', 'فك حجز'),
        ('refund', 'استرداد'),
        ('adjustment', 'تعديل إداري'),
        ('bonus', 'مكافأة'),
    ]

    DIRECTION_CHOICES = [
        ('credit', 'إضافة'),
        ('debit', 'خصم'),
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

    def __str__(self):
        return f'{self.wallet.user} - {self.amount} ساعة'


class HourHold(models.Model):

    STATUS_CHOICES = [
        ('active', 'محجوز'),
        ('captured', 'تم التحويل'),
        ('released', 'تم فك الحجز'),
        ('cancelled', 'ملغي'),
    ]

    wallet = models.ForeignKey(
        HourWallet,
        on_delete=models.PROTECT,
        related_name='holds',
        verbose_name='المحفظة'
    )

    exchange = models.OneToOneField(
        'exchanges.ExchangeRequest',
        on_delete=models.PROTECT,
        related_name='hour_hold',
        verbose_name='طلب التبادل'
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

    def __str__(self):
        return f'{self.wallet.user} - {self.amount} ساعة'