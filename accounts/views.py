from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme

from projects.models import JoinRequest, Project
from .forms import ProfileForm, SignUpForm
from .models import Profile, Skill


def signup_view(request):
    if request.user.is_authenticated:
        return redirect("projects:dashboard")

    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(
                request,
                f"Welcome to TeamUp, {user.profile.full_name}! Select your technical skills below to get matched with projects.",
            )
            return redirect("accounts:profile_edit")
        else:
            messages.error(request, "Please correct the errors highlighted below.")
    else:
        form = SignUpForm()

    return render(request, "accounts/signup.html", {"form": form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect("projects:dashboard")

    next_url = request.GET.get("next") or request.POST.get("next") or ""

    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f"Welcome back, {user.username}!")
            if next_url and url_has_allowed_host_and_scheme(
                url=next_url,
                allowed_hosts={request.get_host()},
                require_https=request.is_secure(),
            ):
                return redirect(next_url)
            return redirect("projects:dashboard")
        else:
            messages.error(request, "Invalid username or password.")
    else:
        form = AuthenticationForm()

    return render(
        request,
        "accounts/login.html",
        {"form": form, "next": next_url},
    )


def logout_view(request):
    if request.method == "POST":
        logout(request)
        messages.info(request, "You have been logged out.")
        return redirect("projects:project_list")
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect("projects:project_list")


@login_required
def student_directory_view(request):
    """
    Searchable, paginated Student Directory allowing peers to filter students
    by keyword (name/username/bio), technical skill, branch, and year of study.
    """
    queryset = (
        Profile.objects.select_related("user")
        .prefetch_related("skills")
        .annotate(
            projects_count=Count("user__owned_projects", distinct=True),
        )
        .order_by("full_name", "user__username")
    )

    q = request.GET.get("q", "").strip()
    skill_slug = request.GET.get("skill", "").strip()
    branch = request.GET.get("branch", "").strip()
    year = request.GET.get("year", "").strip()

    if q:
        queryset = queryset.filter(
            Q(full_name__icontains=q)
            | Q(user__username__icontains=q)
            | Q(bio__icontains=q)
        )

    if skill_slug:
        queryset = queryset.filter(skills__slug=skill_slug)

    if branch:
        queryset = queryset.filter(branch__iexact=branch)

    if year.isdigit() and int(year) in dict(Profile.YEAR_CHOICES):
        queryset = queryset.filter(year_of_study=int(year))

    queryset = queryset.distinct()

    paginator = Paginator(queryset, 9)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    all_skills = Skill.objects.all()
    available_branches = (
        Profile.objects.exclude(branch="")
        .values_list("branch", flat=True)
        .distinct()
        .order_by("branch")
    )

    context = {
        "page_obj": page_obj,
        "all_skills": all_skills,
        "available_branches": available_branches,
        "year_choices": Profile.YEAR_CHOICES,
        "current_q": q,
        "current_skill": skill_slug,
        "current_branch": branch,
        "current_year": year,
    }
    return render(request, "accounts/student_directory.html", context)


@login_required
def profile_detail_view(request, username):
    member = get_object_or_404(
        User.objects.select_related("profile").prefetch_related(
            "profile__skills", "owned_projects__skills_needed"
        ),
        username=username,
    )

    member_projects = list(member.owned_projects.all())
    for proj in member_projects:
        proj.match_score = proj.calculate_match_score(request.user)

    # Fetch the logged-in visitor's Open projects that this student hasn't applied to yet
    invitable_projects = []
    if request.user != member:
        invitable_projects = list(
            Project.objects.filter(
                owner=request.user,
                status=Project.STATUS_OPEN,
            )
            .exclude(join_requests__applicant=member)
            .prefetch_related("skills_needed")
        )
        for proj in invitable_projects:
            proj.candidate_match = proj.calculate_match_score(member)

    return render(
        request,
        "accounts/profile_detail.html",
        {
            "member": member,
            "profile": member.profile,
            "member_projects": member_projects,
            "invitable_projects": invitable_projects,
        },
    )


@login_required
def invite_student_to_project_view(request, username):
    """
    Allow a project owner to send an email invitation to a student profile
    with a direct link to view and apply to the owner's Open project.
    """
    if request.method != "POST":
        return redirect("accounts:profile_detail", username=username)

    candidate = get_object_or_404(
        User.objects.select_related("profile").prefetch_related("profile__skills"),
        username=username,
    )

    if candidate == request.user:
        messages.error(request, "You cannot send a project invitation to yourself.")
        return redirect("accounts:profile_detail", username=username)

    project_id = request.POST.get("project_id", "").strip()
    custom_note = request.POST.get("note", "").strip()

    project = get_object_or_404(
        Project.objects.select_related("owner", "owner__profile").prefetch_related(
            "skills_needed"
        ),
        pk=project_id,
    )

    if project.owner != request.user:
        raise PermissionDenied("You can only invite students to projects that you own.")

    if project.status != Project.STATUS_OPEN:
        messages.error(
            request,
            f"Project '{project.title}' is closed and cannot send new invitations.",
        )
        return redirect("accounts:profile_detail", username=username)

    if JoinRequest.objects.filter(project=project, applicant=candidate).exists():
        messages.warning(
            request,
            f"{candidate.profile.full_name or candidate.username} has already applied to '{project.title}'.",
        )
        return redirect("accounts:profile_detail", username=username)

    project_url = request.build_absolute_uri(
        reverse("projects:project_detail", args=[project.pk])
    )
    owner_name = request.user.profile.full_name or request.user.username
    candidate_name = candidate.profile.full_name or candidate.username
    match_score = project.calculate_match_score(candidate)
    skills_list = ", ".join(s.name for s in project.skills_needed.all())

    note_block = (
        f'\nPersonal note from {owner_name}:\n"{custom_note}"\n'
        if custom_note
        else ""
    )

    if candidate.email:
        send_mail(
            subject=f"[TeamUp] {owner_name} invited you to join '{project.title}'",
            message=(
                f"Hi {candidate_name},\n\n"
                f"{owner_name} (@{request.user.username}) saw your student profile on TeamUp "
                f"and invited you to apply to their {project.get_category_display()} project:\n\n"
                f"Project: {project.title}\n"
                f"Skills Needed: {skills_list}\n"
                f"Your Skill Match: {match_score}%\n"
                f"Application Deadline: {project.deadline.strftime('%b %d, %Y')}\n"
                f"{note_block}\n"
                f"Review the project details and submit your join request here:\n"
                f"{project_url}\n\n"
                f"— TeamUp CSE Collaboration Portal"
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[candidate.email],
            fail_silently=True,
        )

    messages.success(
        request,
        f"Invitation sent to {candidate_name} for '{project.title}'!",
    )
    return redirect("accounts:profile_detail", username=username)


@login_required
def profile_edit_view(request):
    profile = request.user.profile
    if request.method == "POST":
        form = ProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Your student profile and skills have been updated!")
            return redirect("accounts:profile_detail", username=request.user.username)
        else:
            messages.error(request, "Please fix the errors in your profile form.")
    else:
        form = ProfileForm(instance=profile)

    return render(request, "accounts/profile_form.html", {"form": form})


def toggle_theme_view(request, mode):
    """Set a browser cookie for 'light' or 'dark' UI theme and redirect back."""
    chosen_theme = "dark" if mode == "dark" else "light"
    referer = request.META.get("HTTP_REFERER", "/")
    if not url_has_allowed_host_and_scheme(
        url=referer,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        referer = "/"
    response = redirect(referer)
    # Persist theme preference for 30 days
    response.set_cookie("theme", chosen_theme, max_age=30 * 24 * 60 * 60, samesite="Lax")
    return response


def api_profile_detail_view(request, username):
    """
    Lightweight JSON API endpoint returning a student's public profile,
    skills, and owned projects.
    """
    if request.method != "GET":
        return JsonResponse({"error": "Only GET requests are allowed."}, status=405)

    member = (
        User.objects.select_related("profile")
        .prefetch_related("profile__skills", "owned_projects__skills_needed")
        .filter(username=username)
        .first()
    )
    if not member or not hasattr(member, "profile"):
        return JsonResponse(
            {"error": f"Student profile '{username}' not found."},
            status=404,
        )

    profile = member.profile
    owned_projects_payload = []
    for project in member.owned_projects.all():
        owned_projects_payload.append(
            {
                "id": project.pk,
                "title": project.title,
                "category": {
                    "slug": project.category,
                    "label": project.get_category_display(),
                },
                "status": project.status,
                "team_size_needed": project.team_size_needed,
                "deadline": project.deadline.isoformat(),
                "skills_needed": [
                    {"name": s.name, "slug": s.slug}
                    for s in project.skills_needed.all()
                ],
                "detail_url": request.build_absolute_uri(
                    reverse("projects:project_detail", args=[project.pk])
                ),
            }
        )

    payload = {
        "username": member.username,
        "full_name": profile.full_name or member.username,
        "branch": profile.branch,
        "year_of_study": {
            "number": profile.year_of_study,
            "label": profile.get_year_of_study_display(),
        },
        "bio": profile.bio,
        "github_url": profile.github_url,
        "skills": [
            {"name": s.name, "slug": s.slug}
            for s in profile.skills.all()
        ],
        "owned_projects_count": len(owned_projects_payload),
        "owned_projects": owned_projects_payload,
        "profile_url": request.build_absolute_uri(
            reverse("accounts:profile_detail", args=[member.username])
        ),
    }

    return JsonResponse(payload, json_dumps_params={"indent": 2})
