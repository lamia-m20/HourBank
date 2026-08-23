from django.contrib import admin
from .models import (
    FavoriteOffer,
    FavoriteProvider,
    MatchSuggestion,
)


@admin.register(FavoriteOffer)
class FavoriteOfferAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'offer',
        'created_at',
    )

    search_fields = (
        'user__username',
        'user__email',
        'offer__title',
    )

    readonly_fields = (
        'created_at',
    )


@admin.register(FavoriteProvider)
class FavoriteProviderAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'provider',
        'created_at',
    )

    search_fields = (
        'user__username',
        'user__email',
        'provider__username',
        'provider__email',
    )

    readonly_fields = (
        'created_at',
    )


@admin.register(MatchSuggestion)
class MatchSuggestionAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'matched_user',
        'offered_skill',
        'wanted_skill',
        'match_score',
        'is_seen',
        'created_at',
    )

    list_filter = (
        'is_seen',
        'offered_skill',
        'wanted_skill',
    )

    search_fields = (
        'user__username',
        'matched_user__username',
        'offered_skill__name',
        'wanted_skill__name',
    )

    readonly_fields = (
        'created_at',
    )