from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _


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

    client_id = models.UUIDField(
        null=True, blank=True, editable=False, verbose_name=_('Client message ID'),
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
        constraints = [
            models.UniqueConstraint(
                fields=['conversation', 'sender', 'client_id'],
                condition=models.Q(client_id__isnull=False),
                name='unique_sender_client_message',
            )
        ]

    def __str__(self):
        return f'{self.sender} - {self.created_at}'


class CallSignal(models.Model):
    SIGNAL_TYPES = [
        ('offer', _('Offer')), ('answer', _('Answer')),
        ('candidate', _('ICE candidate')), ('hangup', _('Hang up')),
    ]
    session = models.ForeignKey(
        'exchanges.Session', on_delete=models.CASCADE,
        related_name='call_signals', verbose_name=_('Session'),
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='call_signals', verbose_name=_('Sender'),
    )
    signal_type = models.CharField(max_length=20, choices=SIGNAL_TYPES)
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['id']
        indexes = [
            models.Index(fields=['session', 'created_at'], name='call_signal_session_time_idx'),
        ]


class CallEvent(models.Model):
    CALL_TYPES = [('audio', _('Audio call')), ('video', _('Video call'))]
    STATUSES = [
        ('ringing', _('Calling')), ('answered', _('Answered')),
        ('ended', _('Call ended')), ('missed', _('Missed call')),
        ('declined', _('Call declined')), ('cancelled', _('Call cancelled')),
    ]
    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name='call_events',
    )
    session = models.ForeignKey(
        'exchanges.Session', on_delete=models.CASCADE, related_name='call_events',
    )
    caller = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='started_call_events',
    )
    client_id = models.UUIDField(unique=True, editable=False)
    call_type = models.CharField(max_length=10, choices=CALL_TYPES)
    status = models.CharField(max_length=12, choices=STATUSES, default='ringing')
    started_at = models.DateTimeField(auto_now_add=True)
    answered_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['started_at', 'id']
        indexes = [
            models.Index(fields=['conversation', 'started_at'], name='call_event_conv_time_idx'),
            models.Index(fields=['status', 'ended_at'], name='call_event_status_end_idx'),
        ]


class ConversationSystemEvent(models.Model):
    EVENT_TYPES = [('reward', _('Session reward')), ('dispute', _('Session issue'))]
    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name='system_events',
    )
    session = models.ForeignKey(
        'exchanges.Session', on_delete=models.CASCADE, related_name='conversation_events',
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name='conversation_system_events',
    )
    event_type = models.CharField(max_length=20, choices=EVENT_TYPES)
    data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at', 'id']
        constraints = [models.UniqueConstraint(
            fields=['session', 'event_type'], name='unique_session_system_event_type',
        )]


class Notification(models.Model):

    TYPE_CHOICES = [
        ('exchange_request', _('Exchange request')), ('exchange_accepted', _('Exchange accepted')),
        ('exchange_rejected', _('Exchange rejected')), ('session_reminder', _('Session reminder')),
        ('session_completed', _('Session completed')), ('wallet', _('Wallet')),
        ('message', _('New message')), ('review', _('Review')), ('dispute', _('Dispute')),
        ('system', _('System')),
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
        ('open', _('Open')), ('under_review', _('Under review')), ('resolved', _('Resolved')),
        ('rejected', _('Rejected')), ('closed', _('Closed')),
    ]

    REASON_CHOICES = [
        ('no_teaching', _('The other participant did not teach the agreed content')),
        ('no_show', _('The other participant did not attend the session')),
        ('ended_early', _('The session ended before the agreed time')),
        ('poor_teaching_style', _('The teaching style was not suitable')),
        ('inappropriate_behavior', _('There was inappropriate behavior')),
        ('different_content', _('The content differed from the offer description')),
        ('technical_issue', _('Technical issue')), ('other', _('Other')),
        ('incomplete', _('Incomplete session')), ('quality', _('Service quality')),
        ('hours', _('Hours disagreement')), ('behavior', _('Inappropriate behavior')),
    ]

    exchange = models.ForeignKey(
        'exchanges.ExchangeRequest',
        on_delete=models.PROTECT,
        related_name='disputes',
        verbose_name='طلب التبادل'
    )

    session = models.ForeignKey(
        'exchanges.Session', on_delete=models.CASCADE, related_name='disputes',
        null=True, blank=True, verbose_name=_('Session'),
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
        constraints = [models.UniqueConstraint(
            fields=['session'], condition=models.Q(session__isnull=False),
            name='unique_dispute_per_session',
        )]

    def __str__(self):
        return f'نزاع #{self.pk} - {self.exchange}'
