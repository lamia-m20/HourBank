from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class SkillCategory(models.Model):

    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name='اسم التصنيف'
    )

    description = models.TextField(
        blank=True,
        verbose_name='وصف التصنيف'
    )

    icon = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='الأيقونة'
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name='نشط'
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='تاريخ الإنشاء'
    )

    class Meta:
        verbose_name = 'تصنيف مهارة'
        verbose_name_plural = 'تصنيفات المهارات'
        ordering = ['name']

    def __str__(self):
        return self.name


class Skill(models.Model):

    category = models.ForeignKey(
        SkillCategory,
        on_delete=models.CASCADE,
        related_name='skills',
        verbose_name='التصنيف'
    )

    name = models.CharField(
        max_length=150,
        verbose_name='اسم المهارة'
    )

    description = models.TextField(
        blank=True,
        verbose_name='الوصف'
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name='نشطة'
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='تاريخ الإنشاء'
    )

    class Meta:
        verbose_name = 'مهارة'
        verbose_name_plural = 'المهارات'
        ordering = ['name']

        constraints = [
            models.UniqueConstraint(
                fields=['category', 'name'],
                name='unique_skill_per_category'
            )
        ]

    def __str__(self):
        return self.name


class SkillOffer(models.Model):

    LEVEL_CHOICES = [
        ('beginner', _('Beginner')), ('intermediate', _('Intermediate')),
        ('advanced', _('Advanced')), ('expert', _('Expert')),
    ]

    DELIVERY_CHOICES = [
        ('online', _('Remote')), ('in_person', _('In person')),
        ('both', _('Remote and in person')),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='skill_offers',
        verbose_name='مقدم المهارة'
    )

    skill = models.ForeignKey(
        Skill,
        on_delete=models.CASCADE,
        related_name='offers',
        verbose_name='المهارة'
    )

    title = models.CharField(
        max_length=200,
        verbose_name='عنوان العرض'
    )

    description = models.TextField(
        verbose_name='تفاصيل العرض'
    )

    level = models.CharField(
        max_length=20,
        choices=LEVEL_CHOICES,
        default='intermediate',
        verbose_name='مستوى مقدم المهارة'
    )

    delivery_method = models.CharField(
        max_length=20,
        choices=DELIVERY_CHOICES,
        default='online',
        verbose_name='طريقة تقديم الجلسة'
    )

    session_duration_minutes = models.PositiveIntegerField(
        default=60,
        verbose_name='مدة الجلسة بالدقائق'
    )

    hour_cost = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=1,
        verbose_name='تكلفة الجلسة بالساعات'
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name='العرض متاح'
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
        verbose_name = 'عرض مهارة'
        verbose_name_plural = 'عروض المهارات'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user} - {self.skill}'


class SkillRequest(models.Model):

    LEVEL_CHOICES = [
        ('beginner', _('Beginner')), ('intermediate', _('Intermediate')),
        ('advanced', _('Advanced')), ('any', _('Any level')),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='wanted_skills',
        verbose_name='المستخدم'
    )

    skill = models.ForeignKey(
        Skill,
        on_delete=models.CASCADE,
        related_name='requests',
        verbose_name='المهارة المطلوبة'
    )

    desired_level = models.CharField(
        max_length=20,
        choices=LEVEL_CHOICES,
        default='any',
        verbose_name='المستوى المطلوب'
    )

    notes = models.TextField(
        blank=True,
        verbose_name='ملاحظات'
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name='الطلب نشط'
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='تاريخ الطلب'
    )

    class Meta:
        verbose_name = 'مهارة مطلوبة'
        verbose_name_plural = 'المهارات المطلوبة'
        ordering = ['-created_at']

        constraints = [
            models.UniqueConstraint(
                fields=['user', 'skill'],
                name='unique_wanted_skill_per_user'
            )
        ]

    def __str__(self):
        return f'{self.user} يريد تعلم {self.skill}'
