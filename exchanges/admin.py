from django.contrib import admin
from .models import (
    ExchangeRequest,
    ProviderAvailability,
    Session,
    SessionConfirmation,
    ExchangeHistory,
)


@admin.register(ExchangeRequest)
class ExchangeRequestAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'requester',
        'provider',
        'offer',
        'requested_hours',
        'status',
        'requested_date',
        'created_at',
    )

    list_filter = (
        'status',
        'requested_date',
        'created_at',
    )

    search_fields = (
        'requester__username',
        'requester__email',
        'provider__username',
        'provider__email',
        'offer__title',
    )

    readonly_fields = (
        'created_at',
        'updated_at',
    )


@admin.register(ProviderAvailability)
class ProviderAvailabilityAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'day_of_week',
        'start_time',
        'end_time',
        'is_active',
    )

    list_filter = (
        'day_of_week',
        'is_active',
    )

    search_fields = (
        'user__username',
        'user__email',
    )


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'exchange',
        'scheduled_start',
        'scheduled_end',
        'delivery_method',
        'status',
        'completed_at',
    )

    list_filter = (
        'status',
        'delivery_method',
        'scheduled_start',
    )

    search_fields = (
        'exchange__requester__username',
        'exchange__provider__username',
        'meeting_link',
        'location',
    )

    readonly_fields = (
        'created_at',
        'updated_at',
    )


@admin.register(SessionConfirmation)
class SessionConfirmationAdmin(admin.ModelAdmin):
    list_display = (
        'session',
        'user',
        'confirmed',
        'issue_reported',
        'confirmed_at',
    )

    list_filter = (
        'confirmed',
        'issue_reported',
    )

    search_fields = (
        'user__username',
        'user__email',
    )


@admin.register(ExchangeHistory)
class ExchangeHistoryAdmin(admin.ModelAdmin):
    list_display = (
        'exchange',
        'changed_by',
        'old_status',
        'new_status',
        'created_at',
    )

    list_filter = (
        'old_status',
        'new_status',
    )

    search_fields = (
        'exchange__requester__username',
        'exchange__provider__username',
        'changed_by__username',
        'notes',
    )

    readonly_fields = (
        'created_at',
    )