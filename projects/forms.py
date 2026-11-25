from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import JoinRequest, Project


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = [
            "title",
            "description",
            "category",
            "skills_needed",
            "team_size_needed",
            "deadline",
            "status",
        ]
        widgets = {
            "description": forms.Textarea(
                attrs={
                    "rows": 4,
                    "placeholder": "Describe the problem statement, goal, target competition/course, and teammate responsibilities...",
                }
            ),
            "deadline": forms.DateInput(attrs={"type": "date"}),
            "skills_needed": forms.CheckboxSelectMultiple(),
        }

    def clean_title(self):
        title = self.cleaned_data.get("title", "").strip()
        if len(title) < 5:
            raise ValidationError("Project title must be at least 5 characters long.")
        return title

    def clean_team_size_needed(self):
        size = self.cleaned_data.get("team_size_needed")
        if size is None or size < 2 or size > 10:
            raise ValidationError("Team size needed must be between 2 and 10 members.")
        return size

    def clean_deadline(self):
        deadline = self.cleaned_data.get("deadline")
        if deadline and deadline <= timezone.localdate():
            raise ValidationError("Application deadline must be a date in the future.")
        return deadline


class JoinRequestForm(forms.ModelForm):
    class Meta:
        model = JoinRequest
        fields = ["message"]
        widgets = {
            "message": forms.Textarea(
                attrs={
                    "rows": 3,
                    "placeholder": "Hi! I have experience with the required tech stack and would love to join your team...",
                }
            )
        }

    def clean_message(self):
        msg = self.cleaned_data.get("message", "").strip()
        if len(msg) < 10:
            raise ValidationError("Please write a short pitch of at least 10 characters.")
        return msg
