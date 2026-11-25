from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from .models import Profile


class SignUpForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        help_text="Use your university email address.",
    )
    full_name = forms.CharField(
        max_length=120,
        required=True,
        help_text="Your full name as on university records.",
    )
    year_of_study = forms.ChoiceField(
        choices=Profile.YEAR_CHOICES,
        initial=2,
    )
    branch = forms.CharField(
        max_length=60,
        initial="CSE",
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = (
            "username",
            "email",
            "full_name",
            "year_of_study",
            "branch",
            "password1",
            "password2",
        )

    def clean_email(self):
        email = self.cleaned_data.get("email", "").strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("A student account with this email already exists.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
            profile = user.profile
            profile.full_name = self.cleaned_data["full_name"]
            profile.year_of_study = int(self.cleaned_data["year_of_study"])
            profile.branch = self.cleaned_data["branch"]
            profile.save()
        return user


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = [
            "full_name",
            "year_of_study",
            "branch",
            "bio",
            "github_url",
            "skills",
        ]
        widgets = {
            "bio": forms.Textarea(
                attrs={
                    "rows": 4,
                    "placeholder": "Tell teammates about your experience, interests, and past hackathons...",
                }
            ),
            "github_url": forms.URLInput(
                attrs={"placeholder": "https://github.com/yourusername"}
            ),
            "skills": forms.CheckboxSelectMultiple(),
        }

    def clean_github_url(self):
        url = self.cleaned_data.get("github_url", "").strip()
        if url and not url.startswith("https://github.com/"):
            raise ValidationError("GitHub URL must start with https://github.com/")
        return url
