from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Skill",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=50, unique=True)),
                ("slug", models.SlugField(max_length=60, unique=True)),
            ],
            options={
                "ordering": ["name"],
            },
        ),
        migrations.CreateModel(
            name="Profile",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("full_name", models.CharField(blank=True, max_length=120)),
                (
                    "year_of_study",
                    models.PositiveSmallIntegerField(
                        choices=[
                            (1, "1st Year"),
                            (2, "2nd Year"),
                            (3, "3rd Year"),
                            (4, "4th Year"),
                        ],
                        default=1,
                    ),
                ),
                ("branch", models.CharField(default="CSE", max_length=60)),
                ("bio", models.TextField(blank=True)),
                ("github_url", models.URLField(blank=True)),
                (
                    "skills",
                    models.ManyToManyField(
                        blank=True, related_name="profiles", to="accounts.skill"
                    ),
                ),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="profile",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["user__username"],
            },
        ),
    ]
