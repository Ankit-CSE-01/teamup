from django.contrib.auth.models import User
from django.db import models
from accounts.models import Skill


class Project(models.Model):
    CATEGORY_HACKATHON = "hackathon"
    CATEGORY_MINI = "mini-project"
    CATEGORY_MAJOR = "major-project"
    CATEGORY_RESEARCH = "research"
    CATEGORY_STARTUP = "startup"

    CATEGORY_CHOICES = [
        (CATEGORY_HACKATHON, "Hackathon"),
        (CATEGORY_MINI, "Mini Project"),
        (CATEGORY_MAJOR, "Major Project"),
        (CATEGORY_RESEARCH, "Research"),
        (CATEGORY_STARTUP, "Startup"),
    ]

    STATUS_OPEN = "Open"
    STATUS_CLOSED = "Closed"

    STATUS_CHOICES = [
        (STATUS_OPEN, "Open"),
        (STATUS_CLOSED, "Closed"),
    ]

    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="owned_projects",
    )
    title = models.CharField(max_length=150)
    description = models.TextField()
    category = models.CharField(
        max_length=30,
        choices=CATEGORY_CHOICES,
        default=CATEGORY_HACKATHON,
    )
    skills_needed = models.ManyToManyField(
        Skill,
        related_name="projects",
        blank=False,
    )
    team_size_needed = models.PositiveSmallIntegerField(default=3)
    deadline = models.DateField()
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default=STATUS_OPEN,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} ({self.get_category_display()})"

    def calculate_match_score(self, user):
        """
        Return integer percentage (0-100) of overlap between user's profile skills
        and this project's skills_needed.
        """
        if not user or not user.is_authenticated or not hasattr(user, "profile"):
            return 0

        project_skill_ids = {skill.id for skill in self.skills_needed.all()}
        if not project_skill_ids:
            return 0

        user_skill_ids = {skill.id for skill in user.profile.skills.all()}
        overlap = len(project_skill_ids.intersection(user_skill_ids))
        return round((overlap / len(project_skill_ids)) * 100)


class JoinRequest(models.Model):
    STATUS_PENDING = "Pending"
    STATUS_ACCEPTED = "Accepted"
    STATUS_REJECTED = "Rejected"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_ACCEPTED, "Accepted"),
        (STATUS_REJECTED, "Rejected"),
    ]

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="join_requests",
    )
    applicant = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="applications",
    )
    message = models.TextField(
        max_length=500,
        help_text="Briefly explain your relevant skills and how you can contribute.",
    )
    status = models.CharField(
        max_length=12,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["project", "applicant"],
                name="unique_project_applicant",
            )
        ]

    def __str__(self):
        return f"{self.applicant.username} -> {self.project.title} [{self.status}]"
