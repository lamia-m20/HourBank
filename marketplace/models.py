from django.conf import settings
from django.db import models


class FavoriteOffer(models.Model):

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='favorite_offers',
        verbose_name='المستخدم'
    )

    offer = models.ForeignKey(
        'skills.SkillOffer',
        on_delete=models.CASCADE,
        related_name='favorited_by',
        verbose_name='عرض المهارة'
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='تاريخ الإضافة'
    )

    class Meta:
        verbose_name = 'عرض محفوظ'
        verbose_name_plural = 'العروض المحفوظة'

        constraints = [
            models.UniqueConstraint(
                fields=['user', 'offer'],
                name='unique_favorite_offer'
            )
        ]

    def __str__(self):
        return f'{self.user} - {self.offer}'


class FavoriteProvider(models.Model):

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='favorite_providers',
        verbose_name='المستخدم'
    )

    provider = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='saved_by_users',
        verbose_name='مقدم المهارة'
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='تاريخ الإضافة'
    )

    class Meta:
        verbose_name = 'مقدم مهارة محفوظ'
        verbose_name_plural = 'مقدمو المهارات المحفوظون'

        constraints = [
            models.UniqueConstraint(
                fields=['user', 'provider'],
                name='unique_favorite_provider'
            )
        ]

    def __str__(self):
        return f'{self.user} → {self.provider}'


class MatchSuggestion(models.Model):

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='match_suggestions',
        verbose_name='المستخدم'
    )

    matched_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='matched_for_users',
        verbose_name='المستخدم المقترح'
    )

    offered_skill = models.ForeignKey(
        'skills.Skill',
        on_delete=models.CASCADE,
        related_name='marketplace_offered_matches',
        verbose_name='المهارة المقدمة'
    )

    wanted_skill = models.ForeignKey(
        'skills.Skill',
        on_delete=models.CASCADE,
        related_name='marketplace_wanted_matches',
        verbose_name='المهارة المطلوبة'
    )

    match_score = models.PositiveIntegerField(
        default=0,
        verbose_name='درجة التطابق'
    )

    is_seen = models.BooleanField(
        default=False,
        verbose_name='تمت مشاهدة الاقتراح'
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='تاريخ الاقتراح'
    )

    class Meta:
        verbose_name = 'اقتراح تطابق'
        verbose_name_plural = 'اقتراحات التطابق'
        ordering = ['-match_score', '-created_at']

    def __str__(self):
        return f'{self.user} ↔ {self.matched_user}'