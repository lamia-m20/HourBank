from django.contrib import admin
from .models import (
    SkillCategory,
    Skill,
    SkillOffer,
    SkillRequest,
)


@admin.register(SkillCategory)
class SkillCategoryAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'is_active',
        'created_at',
    )

    list_filter = (
        'is_active',
    )

    search_fields = (
        'name',
        'description',
    )


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'category',
        'is_active',
        'created_at',
    )

    list_filter = (
        'category',
        'is_active',
    )

    search_fields = (
        'name',
        'description',
    )


@admin.register(SkillOffer)
class SkillOfferAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'user',
        'skill',
        'level',
        'delivery_method',
        'session_duration_minutes',
        'hour_cost',
        'is_active',
        'created_at',
    )

    list_filter = (
        'level',
        'delivery_method',
        'is_active',
        'skill',
    )

    search_fields = (
        'title',
        'description',
        'user__username',
        'user__email',
        'skill__name',
    )

    readonly_fields = (
        'created_at',
        'updated_at',
    )


@admin.register(SkillRequest)
class SkillRequestAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'skill',
        'desired_level',
        'is_active',
        'created_at',
    )

    list_filter = (
        'desired_level',
        'is_active',
        'skill',
    )

    search_fields = (
        'user__username',
        'user__email',
        'skill__name',
        'notes',
    )

    readonly_fields = (
        'created_at',
    )