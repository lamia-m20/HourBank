from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Conversation(models.Model):

    exchange = models.OneToOneField(
        'exchanges.ExchangeRequest',
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name='conversation',
        verbose_name='طلب التبادل'
    )

    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through='ConversationParticipant',
        related_name='conversations',
        verbose_name='المشاركون'
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='تاريخ إنشاء المحادثة'
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='آخر تحديث'
    )

    class Meta:
        verbose_name = 'محادثة'
        verbose_name_plural = 'المحادثات'
        ordering = ['-updated_at']

    def __str__(self):
        return f'محادثة #{self.pk}'


class ConversationParticipant(models.Model):

    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='conversation_participants',
        verbose_name='المحادثة'
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='conversation_memberships',
        verbose_name='المستخدم'
    )

    joined_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='تاريخ الانضمام'
    )

    last_read_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='آخر قراءة'
    )

    class Meta:
        verbose_name = 'مشارك في محادثة'
        verbose_name_plural = 'المشاركون في المحادثات'

        constraints = [
            models.UniqueConstraint(
                fields=['conversation', 'user'],
                name='unique_conversation_participant'
            )
        ]

    def __str__(self):
        return f'{self.user} - {self.conversation}'


class Message(models.Model):

    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='messages',
        verbose_name='المحادثة'
    )

    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_messages',
        verbose_name='المرسل'
    )

    content = models.TextField(
        verbose_name='محتوى الرسالة'
    )

    is_edited = models.BooleanField(
        default=False,
        verbose_name='تم تعديل الرسالة'
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='وقت الإرسال'
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='آخر تعديل'
    )

    class Meta:
        verbose_name = 'رسالة'
        verbose_name_plural = 'الرسائل'
        ordering = ['created_at']

    def __str__(self):
        return f'{self.sender} - {self.created_at}'


class Notification(models.Model):

    TYPE_CHOICES = [
        ('exchange_request', 'طلب تبادل'),
        ('exchange_accepted', 'قبول طلب'),
        ('exchange_rejected', 'رفض طلب'),
        ('session_reminder', 'تذكير جلسة'),
        ('session_completed', 'اكتمال جلسة'),
        ('wallet', 'المحفظة'),
        ('message', 'رسالة جديدة'),
        ('review', 'تقييم'),
        ('dispute', 'نزاع'),
        ('system', 'النظام'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name='المستخدم'
    )

    notification_type = models.CharField(
        max_length=30,
        choices=TYPE_CHOICES,
        default='system',
        verbose_name='نوع الإشعار'
    )

    title = models.CharField(
        max_length=200,
        verbose_name='العنوان'
    )

    message = models.TextField(
        verbose_name='نص الإشعار'
    )

    target_url = models.CharField(
        max_length=500,
        blank=True,
        verbose_name='رابط الإشعار'
    )

    is_read = models.BooleanField(
        default=False,
        verbose_name='تمت القراءة'
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='تاريخ الإشعار'
    )

    class Meta:
        verbose_name = 'إشعار'
        verbose_name_plural = 'الإشعارات'
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class Review(models.Model):

    exchange = models.ForeignKey(
        'exchanges.ExchangeRequest',
        on_delete=models.CASCADE,
        related_name='reviews',
        verbose_name='طلب التبادل'
    )

    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reviews_written',
        verbose_name='كاتب التقييم'
    )

    reviewed_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reviews_received',
        verbose_name='المستخدم المقيم'
    )

    rating = models.PositiveSmallIntegerField(
        validators=[
            MinValueValidator(1),
            MaxValueValidator(5),
        ],
        verbose_name='التقييم العام'
    )

    expertise_rating = models.PositiveSmallIntegerField(
        validators=[
            MinValueValidator(1),
            MaxValueValidator(5),
        ],
        verbose_name='تقييم المهارة'
    )

    communication_rating = models.PositiveSmallIntegerField(
        validators=[
            MinValueValidator(1),
            MaxValueValidator(5),
        ],
        verbose_name='تقييم التواصل'
    )

    punctuality_rating = models.PositiveSmallIntegerField(
        validators=[
            MinValueValidator(1),
            MaxValueValidator(5),
        ],
        verbose_name='تقييم الالتزام'
    )

    comment = models.TextField(
        blank=True,
        verbose_name='التعليق'
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='تاريخ التقييم'
    )

    class Meta:
        verbose_name = 'تقييم'
        verbose_name_plural = 'التقييمات'
        ordering = ['-created_at']

        constraints = [
            models.UniqueConstraint(
                fields=['exchange', 'reviewer', 'reviewed_user'],
                name='unique_review_per_exchange'
            )
        ]

    def __str__(self):
        return f'{self.reviewer} → {self.reviewed_user}'


class Dispute(models.Model):

    STATUS_CHOICES = [
        ('open', 'مفتوح'),
        ('under_review', 'قيد المراجعة'),
        ('resolved', 'تم الحل'),
        ('rejected', 'مرفوض'),
        ('closed', 'مغلق'),
    ]

    REASON_CHOICES = [
        ('no_show', 'عدم حضور الطرف الآخر'),
        ('incomplete', 'الجلسة لم تكتمل'),
        ('quality', 'مشكلة في جودة الخدمة'),
        ('hours', 'خلاف على الساعات'),
        ('behavior', 'سلوك غير مناسب'),
        ('other', 'أخرى'),
    ]

    exchange = models.ForeignKey(
        'exchanges.ExchangeRequest',
        on_delete=models.PROTECT,
        related_name='disputes',
        verbose_name='طلب التبادل'
    )

    opened_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='opened_disputes',
        verbose_name='مقدم النزاع'
    )

    against_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='received_disputes',
        verbose_name='الطرف الآخر'
    )

    reason = models.CharField(
        max_length=30,
        choices=REASON_CHOICES,
        verbose_name='سبب النزاع'
    )

    description = models.TextField(
        verbose_name='تفاصيل النزاع'
    )

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default='open',
        verbose_name='حالة النزاع'
    )

    resolution = models.TextField(
        blank=True,
        verbose_name='قرار النزاع'
    )

    admin_notes = models.TextField(
        blank=True,
        verbose_name='ملاحظات الإدارة'
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='تاريخ فتح النزاع'
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='آخر تحديث'
    )

    resolved_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='تاريخ الحل'
    )

    class Meta:
        verbose_name = 'نزاع'
        verbose_name_plural = 'النزاعات'
        ordering = ['-created_at']

    def __str__(self):
        return f'نزاع #{self.pk} - {self.exchange}'