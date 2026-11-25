from django.contrib.auth.models import Group, User
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Profile


@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    """Auto-create a Student Profile when a new User is created."""
    if created:
        full_name = f"{instance.first_name} {instance.last_name}".strip()
        Profile.objects.get_or_create(
            user=instance,
            defaults={"full_name": full_name or instance.username},
        )
        student_group, _ = Group.objects.get_or_create(name="Students")
        instance.groups.add(student_group)
    else:
        if not hasattr(instance, "profile"):
            Profile.objects.get_or_create(user=instance)
