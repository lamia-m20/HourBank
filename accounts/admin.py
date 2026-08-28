from django.contrib import admin
from .models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'account_type',
        'city',
        'country',
        'is_verified',
        'is_available',
        'average_rating',
        'completed_sessions',
        'created_at',
    )

    list_filter = (
        'account_type',
        'is_verified',
        'is_available',
        'country',
    )

    search_fields = (
        'user__username',
        'user__email',
        'city',
        'country',
    )

    readonly_fields = (
        'average_rating',
        'reviews_count',
        'completed_sessions',
        'created_at',
        'updated_at',
    )
