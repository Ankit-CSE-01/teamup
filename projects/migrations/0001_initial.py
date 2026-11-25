from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("accounts", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Project",
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
                ("title", models.CharField(max_length=150)),
                ("description", models.TextField()),
                (
                    "category",
                    models.CharField(
                        choices=[
                            ("hackathon", "Hackathon"),
                            ("mini-project", "Mini Project"),
                            ("major-project", "Major Project"),
                            ("research", "Research"),
                            ("startup", "Startup"),
                        ],
                        default="hackathon",
                        max_length=30,
                    ),
                ),
                ("team_size_needed", models.PositiveSmallIntegerField(default=3)),
                ("deadline", models.DateField()),
                (
                    "status",
                    models.CharField(
                        choices=[("Open", "Open"), ("Closed", "Closed")],
                        default="Open",
                        max_length=10,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "owner",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="owned_projects",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "skills_needed",
                    models.ManyToManyField(
                        related_name="projects", to="accounts.skill"
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="JoinRequest",
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
                (
                    "message",
                    models.TextField(
                        help_text="Briefly explain your relevant skills and how you can contribute.",
                        max_length=500,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("Pending", "Pending"),
                            ("Accepted", "Accepted"),
                            ("Rejected", "Rejected"),
                        ],
                        default="Pending",
                        max_length=12,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "applicant",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="applications",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "project",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="join_requests",
                        to="projects.project",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddConstraint(
            model_name="joinrequest",
            constraint=models.UniqueConstraint(
                fields=("project", "applicant"), name="unique_project_applicant"
            ),
        ),
    ]
