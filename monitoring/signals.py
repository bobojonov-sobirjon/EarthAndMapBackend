import json

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from lands.models import PublicLand

from .models import ChangeLog


@receiver(pre_save, sender=PublicLand)
def track_land_changes(sender, instance, **kwargs):
    if not instance.pk:
        return
    try:
        old = PublicLand.objects.get(pk=instance.pk)
    except PublicLand.DoesNotExist:
        return

    user = getattr(instance, '_changed_by', None)
    tracked = [
        ('status', ChangeLog.ChangeType.STATUS_CHANGED),
        ('name', ChangeLog.ChangeType.UPDATED),
        ('address', ChangeLog.ChangeType.UPDATED),
    ]

    for field, change_type in tracked:
        old_val = getattr(old, field)
        new_val = getattr(instance, field)
        if old_val != new_val:
            ChangeLog.objects.create(
                land=instance,
                change_type=change_type,
                field_name=field,
                old_value=str(old_val),
                new_value=str(new_val),
                changed_by=user,
            )

    if old.geometry != instance.geometry:
        ChangeLog.objects.create(
            land=instance,
            change_type=ChangeLog.ChangeType.GEOMETRY_CHANGED,
            field_name='geometry',
            description='Geometriya o\'zgartirildi',
            changed_by=user,
        )


@receiver(post_save, sender=PublicLand)
def log_land_creation(sender, instance, created, **kwargs):
    if created:
        ChangeLog.objects.create(
            land=instance,
            change_type=ChangeLog.ChangeType.CREATED,
            description=f'"{instance.name}" obyekti yaratildi',
            changed_by=instance.created_by,
        )
