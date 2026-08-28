from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

from .services import ensure_welcome_credit


@receiver(post_save, sender=get_user_model())
def create_welcome_wallet(sender, instance, created, **kwargs):
    if created:
        ensure_welcome_credit(instance)
