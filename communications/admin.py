from django.contrib import admin
from .models import (
    Conversation,
    ConversationParticipant,
    Message,
    Notification,
    Review,
    Dispute,
)


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'exchange',
        'created_at',
        'updated_at',
    )

    search_fields = (
        'exchange__requester__username',
        'exchange__provider__username',
    )

    readonly_fields = (
        'created_at',
        'updated_at',
    )


@admin.register(ConversationParticipant)
class ConversationParticipantAdmin(admin.ModelAdmin):
    list_display = (
        'conversation',
        'user',
        'joined_at',
        'last_read_at',
    )

    search_fields = (
        'user__username',
        'user__email',
    )

    readonly_fields = (
        'joined_at',
    )


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = (
        'conversation',
        'sender',
        'is_edited',
        'created_at',
    )

    search_fields = (
        'sender__username',
        'sender__email',
        'content',
    )

    list_filter = (
        'is_edited',
        'created_at',
    )

    readonly_fields = (
        'created_at',
        'updated_at',
    )


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'notification_type',
        'title',
        'is_read',
        'created_at',
    )

    list_filter = (
        'notification_type',
        'is_read',
    )

    search_fields = (
        'user__username',
        'user__email',
        'title',
        'message',
    )

    readonly_fields = (
        'created_at',
    )


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = (
        'reviewer',
        'reviewed_user',
        'exchange',
        'rating',
        'expertise_rating',
        'communication_rating',
        'punctuality_rating',
        'created_at',
    )

    list_filter = (
        'rating',
        'expertise_rating',
        'communication_rating',
        'punctuality_rating',
    )

    search_fields = (
        'reviewer__username',
        'reviewed_user__username',
        'comment',
    )

    readonly_fields = (
        'created_at',
    )


@admin.register(Dispute)
class DisputeAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'exchange',
        'session',
        'opened_by',
        'against_user',
        'reason',
        'status',
        'created_at',
        'resolved_at',
    )

    list_filter = (
        'status',
        'reason',
    )

    search_fields = (
        'session__id',
        'opened_by__username',
        'opened_by__email',
        'against_user__username',
        'against_user__email',
        'description',
        'resolution',
    )

    readonly_fields = (
        'created_at',
        'updated_at',
    )
