from django.contrib.auth.models import User
from django.db import models


class Skill(models.Model):
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=60, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Profile(models.Model):
    YEAR_CHOICES = [
        (1, "1st Year"),
        (2, "2nd Year"),
        (3, "3rd Year"),
        (4, "4th Year"),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    full_name = models.CharField(max_length=120, blank=True)
    year_of_study = models.PositiveSmallIntegerField(
        choices=YEAR_CHOICES,
        default=1,
    )
    branch = models.CharField(max_length=60, default="CSE")
    bio = models.TextField(blank=True)
    github_url = models.URLField(blank=True)
    skills = models.ManyToManyField(
        Skill,
        blank=True,
        related_name="profiles",
    )

    class Meta:
        ordering = ["user__username"]

    def __str__(self):
        display = self.full_name or self.user.username
        return f"{display} ({self.branch} - Year {self.year_of_study})"
