from django.conf import settings
from django.db import models


class ExchangeRequest(models.Model):

    STATUS_CHOICES = [
        ('pending', 'بانتظار الموافقة'),
        ('accepted', 'تمت الموافقة'),
        ('rejected', 'مرفوض'),
        ('scheduled', 'تم تحديد الموعد'),
        ('in_progress', 'الجلسة جارية'),
        ('completed', 'مكتمل'),
        ('cancelled', 'ملغي'),
        ('disputed', 'يوجد نزاع'),
    ]

    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_exchange_requests',
        verbose_name='طالب المهارة'
    )

    provider = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='received_exchange_requests',
        verbose_name='مقدم المهارة'
    )

    offer = models.ForeignKey(
        'skills.SkillOffer',
        on_delete=models.PROTECT,
        related_name='exchange_requests',
        verbose_name='عرض المهارة'
    )

    requested_hours = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=1,
        verbose_name='عدد الساعات'
    )

    message = models.TextField(
        blank=True,
        verbose_name='رسالة الطلب'
    )

    requested_date = models.DateField(
        blank=True,
        null=True,
        verbose_name='التاريخ المقترح'
    )

    requested_time = models.TimeField(
        blank=True,
        null=True,
        verbose_name='الوقت المقترح'
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='الحالة'
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='تاريخ الطلب'
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='آخر تحديث'
    )

    class Meta:
        verbose_name = 'طلب تبادل'
        verbose_name_plural = 'طلبات التبادل'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.requester} → {self.provider} - {self.offer}'


class ProviderAvailability(models.Model):

    DAY_CHOICES = [
        (0, 'الاثنين'),
        (1, 'الثلاثاء'),
        (2, 'الأربعاء'),
        (3, 'الخميس'),
        (4, 'الجمعة'),
        (5, 'السبت'),
        (6, 'الأحد'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='availability_slots',
        verbose_name='المستخدم'
    )

    day_of_week = models.PositiveSmallIntegerField(
        choices=DAY_CHOICES,
        verbose_name='اليوم'
    )

    start_time = models.TimeField(
        verbose_name='وقت البداية'
    )

    end_time = models.TimeField(
        verbose_name='وقت النهاية'
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name='متاح'
    )

    class Meta:
        verbose_name = 'وقت توفر'
        verbose_name_plural = 'أوقات التوفر'
        ordering = ['day_of_week', 'start_time']

    def __str__(self):
        return f'{self.user} - {self.get_day_of_week_display()}'


class Session(models.Model):

    STATUS_CHOICES = [
        ('scheduled', 'مجدولة'),
        ('in_progress', 'جارية'),
        ('waiting_confirmation', 'بانتظار التأكيد'),
        ('completed', 'مكتملة'),
        ('cancelled', 'ملغاة'),
        ('disputed', 'متنازع عليها'),
    ]

    DELIVERY_CHOICES = [
        ('online', 'عن بعد'),
        ('in_person', 'حضوري'),
    ]

    exchange = models.OneToOneField(
        ExchangeRequest,
        on_delete=models.CASCADE,
        related_name='session',
        verbose_name='طلب التبادل'
    )

    scheduled_start = models.DateTimeField(
        verbose_name='بداية الجلسة'
    )

    scheduled_end = models.DateTimeField(
        verbose_name='نهاية الجلسة'
    )

    delivery_method = models.CharField(
        max_length=20,
        choices=DELIVERY_CHOICES,
        default='online',
        verbose_name='طريقة الجلسة'
    )

    meeting_link = models.URLField(
        blank=True,
        verbose_name='رابط الجلسة'
    )

    location = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='مكان الجلسة'
    )

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default='scheduled',
        verbose_name='حالة الجلسة'
    )

    started_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='وقت البدء الفعلي'
    )

    completed_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='وقت الإكمال'
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
        verbose_name = 'جلسة'
        verbose_name_plural = 'الجلسات'
        ordering = ['-scheduled_start']

    def __str__(self):
        return f'جلسة #{self.pk}'


class SessionConfirmation(models.Model):

    session = models.ForeignKey(
        Session,
        on_delete=models.CASCADE,
        related_name='confirmations',
        verbose_name='الجلسة'
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='session_confirmations',
        verbose_name='المستخدم'
    )

    confirmed = models.BooleanField(
        default=False,
        verbose_name='تم تأكيد الجلسة'
    )

    issue_reported = models.BooleanField(
        default=False,
        verbose_name='تم الإبلاغ عن مشكلة'
    )

    notes = models.TextField(
        blank=True,
        verbose_name='ملاحظات'
    )

    confirmed_at = models.DateTimeField(
        auto_now=True,
        verbose_name='وقت التأكيد'
    )

    class Meta:
        verbose_name = 'تأكيد جلسة'
        verbose_name_plural = 'تأكيدات الجلسات'

        constraints = [
            models.UniqueConstraint(
                fields=['session', 'user'],
                name='unique_session_confirmation'
            )
        ]

    def __str__(self):
        return f'{self.session} - {self.user}'


class ExchangeHistory(models.Model):

    exchange = models.ForeignKey(
        ExchangeRequest,
        on_delete=models.CASCADE,
        related_name='history',
        verbose_name='طلب التبادل'
    )

    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='exchange_changes',
        verbose_name='تم التعديل بواسطة'
    )

    old_status = models.CharField(
        max_length=30,
        blank=True,
        verbose_name='الحالة السابقة'
    )

    new_status = models.CharField(
        max_length=30,
        verbose_name='الحالة الجديدة'
    )

    notes = models.TextField(
        blank=True,
        verbose_name='ملاحظات'
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='وقت التغيير'
    )

    class Meta:
        verbose_name = 'سجل تبادل'
        verbose_name_plural = 'سجل التبادلات'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.exchange} - {self.new_status}'