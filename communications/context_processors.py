from django.db.models import Count, F, Q

from .models import CallEvent, ConversationParticipant


def unread_messages(request):
    if not request.user.is_authenticated:
        return {'unread_messages_count': 0}
    unread_filter = ~Q(conversation__messages__sender=request.user) & (
        Q(last_read_at__isnull=True)
        | Q(conversation__messages__created_at__gt=F('last_read_at'))
    )
    result = ConversationParticipant.objects.filter(user=request.user).aggregate(
        total=Count('conversation__messages', filter=unread_filter, distinct=True)
    )
    missed_scope = Q()
    for conversation_id, last_read_at in ConversationParticipant.objects.filter(
        user=request.user,
    ).values_list('conversation_id', 'last_read_at'):
        condition = Q(conversation_id=conversation_id)
        if last_read_at:
            condition &= Q(ended_at__gt=last_read_at)
        missed_scope |= condition
    missed = CallEvent.objects.filter(
        missed_scope, status='missed',
    ).exclude(caller=request.user).count() if missed_scope else 0
    return {'unread_messages_count': (result['total'] or 0) + missed}
