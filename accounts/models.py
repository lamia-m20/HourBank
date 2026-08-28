from django.conf import settings
from django.db import models
from cloudinary.models import CloudinaryField
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class UserProfile(models.Model):

    ACCOUNT_TYPE_CHOICES = [
        ('individual', _('Individual')), ('professional', _('Professional')),
        ('trainer', _('Trainer')), ('organization', _('Organization')),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile',
        verbose_name='المستخدم'
    )

    account_type = models.CharField(
        max_length=20,
        choices=ACCOUNT_TYPE_CHOICES,
        default='individual',
        verbose_name='نوع الحساب'
    )

    # ==========================================
    # الصورة الشخصية - Cloudinary
    # ==========================================

    profile_image = CloudinaryField(
        'الصورة الشخصية',
        resource_type='image',
        folder='hourbank/accounts/profile_images',
        blank=True,
        null=True
    )

    bio = models.TextField(
        blank=True,
        verbose_name='نبذة شخصية'
    )

    birth_date = models.DateField(
        _('Date of birth'),
        null=True,
        blank=True,
    )

    city = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='المدينة'
    )

    country = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='الدولة'
    )

    timezone = models.CharField(
        max_length=100,
        default='Asia/Riyadh',
        verbose_name='المنطقة الزمنية'
    )

    preferred_language = models.CharField(
        max_length=20,
        default='ar',
        verbose_name='اللغة المفضلة'
    )

    is_verified = models.BooleanField(
        default=False,
        verbose_name='حساب موثق'
    )

    is_available = models.BooleanField(
        default=True,
        verbose_name='متاح لتقديم المهارات'
    )

    average_rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0,
        verbose_name='متوسط التقييم'
    )

    reviews_count = models.PositiveIntegerField(
        default=0,
        verbose_name='عدد التقييمات'
    )

    completed_sessions = models.PositiveIntegerField(
        default=0,
        verbose_name='الجلسات المكتملة'
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='تاريخ إنشاء الملف'
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='آخر تحديث'
    )

    class Meta:
        verbose_name = 'ملف مستخدم'
        verbose_name_plural = 'ملفات المستخدمين'
        ordering = ['-created_at']

    def __str__(self):
        return self.user.get_username()

    @property
    def age(self):
        if not self.birth_date:
            return None
        today = timezone.localdate()
        return today.year - self.birth_date.year - (
            (today.month, today.day) < (self.birth_date.month, self.birth_date.day)
        )
