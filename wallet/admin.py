from django.contrib import admin
from .models import (
    HourWallet,
    HourTransaction,
    HourHold,
)


@admin.register(HourWallet)
class HourWalletAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'available_balance',
        'held_balance',
        'total_earned',
        'total_spent',
        'updated_at',
    )

    search_fields = (
        'user__username',
        'user__email',
    )

    readonly_fields = (
        'created_at',
        'updated_at',
    )


@admin.register(HourTransaction)
class HourTransactionAdmin(admin.ModelAdmin):
    list_display = (
        'reference',
        'wallet',
        'transaction_type',
        'direction',
        'amount',
        'balance_after',
        'exchange',
        'created_at',
    )

    list_filter = (
        'transaction_type',
        'direction',
        'created_at',
    )

    search_fields = (
        'reference',
        'wallet__user__username',
        'wallet__user__email',
        'description',
    )

    readonly_fields = (
        'reference',
        'created_at',
    )


@admin.register(HourHold)
class HourHoldAdmin(admin.ModelAdmin):
    list_display = (
        'wallet',
        'exchange',
        'amount',
        'status',
        'created_at',
        'released_at',
    )

    list_filter = (
        'status',
    )

    search_fields = (
        'wallet__user__username',
        'wallet__user__email',
    )

    readonly_fields = (
        'created_at',
    )