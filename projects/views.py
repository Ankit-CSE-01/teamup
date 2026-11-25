from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.mail import send_mail, send_mass_mail
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import Count, F, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from accounts.models import Profile, Skill
from .admin import generate_projects_roster_csv
from .forms import JoinRequestForm, ProjectForm
from .models import JoinRequest, Project


def attach_match_scores(projects_iterable, user):
    """Compute and attach `match_score` attribute to each project for templates."""
    project_list = list(projects_iterable)
    for proj in project_list:
        proj.match_score = proj.calculate_match_score(user)
    return project_list


def project_list_view(request, active_category=None):
    """
    Browse & Search view demonstrating ORM filter, Q objects, annotate,
    select_related, prefetch_related, GET query params, and pagination.
    """
    queryset = (
        Project.objects.select_related("owner", "owner__profile")
        .prefetch_related("skills_needed")
        .annotate(
            accepted_count=Count(
                "join_requests",
                filter=Q(join_requests__status=JoinRequest.STATUS_ACCEPTED),
            ),
            total_requests=Count("join_requests"),
        )
    )

    q = request.GET.get("q", "").strip()
    category = active_category or request.GET.get("category", "").strip()
    skill_slug = request.GET.get("skill", "").strip()
    status_filter = request.GET.get("status", "").strip()

    if q:
        queryset = queryset.filter(
            Q(title__icontains=q) | Q(description__icontains=q)
        )

    if category:
        queryset = queryset.filter(category=category)

    if skill_slug:
        queryset = queryset.filter(skills_needed__slug=skill_slug)

    if status_filter in (Project.STATUS_OPEN, Project.STATUS_CLOSED):
        queryset = queryset.filter(status=status_filter)

    queryset = queryset.distinct().order_by("-created_at")

    paginator = Paginator(queryset, 6)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # Attach skill match percentage to each project on the current page
    if request.user.is_authenticated:
        request.user.profile.skills.all()  # warm cache
    for project in page_obj.object_list:
        project.match_score = project.calculate_match_score(request.user)

    all_skills = Skill.objects.all()

    context = {
        "page_obj": page_obj,
        "all_skills": all_skills,
        "category_choices": Project.CATEGORY_CHOICES,
        "status_choices": Project.STATUS_CHOICES,
        "current_q": q,
        "current_category": category,
        "current_skill": skill_slug,
        "current_status": status_filter,
    }
    return render(request, "projects/project_list.html", context)


def category_projects_view(request, slug):
    """URL regex endpoint `^category/(?P<slug>[a-z-]+)/$`."""
    valid_slugs = dict(Project.CATEGORY_CHOICES).keys()
    if slug not in valid_slugs:
        messages.warning(
            request, f"Category '{slug}' was not recognized. Showing all projects."
        )
        return redirect("projects:project_list")
    return project_list_view(request, active_category=slug)


def project_detail_view(request, pk):
    project = get_object_or_404(
        Project.objects.select_related("owner", "owner__profile")
        .prefetch_related("skills_needed", "join_requests__applicant__profile")
        .annotate(
            accepted_count=Count(
                "join_requests",
                filter=Q(join_requests__status=JoinRequest.STATUS_ACCEPTED),
            )
        ),
        pk=pk,
    )
    project.match_score = project.calculate_match_score(request.user)

    # Track last 5 recently viewed project IDs in the user's session
    recent = request.session.get("recently_viewed", [])
    if pk in recent:
        recent.remove(pk)
    recent.insert(0, pk)
    request.session["recently_viewed"] = recent[:5]
    request.session.modified = True

    existing_request = None
    if request.user.is_authenticated:
        existing_request = project.join_requests.filter(applicant=request.user).first()

    accepted_members = project.join_requests.filter(status=JoinRequest.STATUS_ACCEPTED)
    form = JoinRequestForm()

    context = {
        "project": project,
        "existing_request": existing_request,
        "accepted_members": accepted_members,
        "form": form,
    }
    return render(request, "projects/project_detail.html", context)


@login_required
def project_create_view(request):
    if request.method == "POST":
        form = ProjectForm(request.POST)
        if form.is_valid():
            project = form.save(commit=False)
            project.owner = request.user
            project.save()
            form.save_m2m()
            messages.success(request, f"Project '{project.title}' created successfully!")
            return redirect("projects:project_detail", pk=project.pk)
        else:
            messages.error(request, "Please fix the validation errors below.")
    else:
        form = ProjectForm()

    return render(
        request,
        "projects/project_form.html",
        {"form": form, "is_edit": False},
    )


@login_required
def project_edit_view(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if project.owner != request.user:
        raise PermissionDenied("Only the project owner can edit this project.")

    if request.method == "POST":
        form = ProjectForm(request.POST, instance=project)
        if form.is_valid():
            form.save()
            messages.success(request, f"Project '{project.title}' has been updated.")
            return redirect("projects:project_detail", pk=project.pk)
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = ProjectForm(instance=project)

    return render(
        request,
        "projects/project_form.html",
        {"form": form, "project": project, "is_edit": True},
    )


@login_required
def project_delete_view(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if project.owner != request.user:
        raise PermissionDenied("Only the project owner can delete this project.")

    if request.method == "POST":
        title = project.title
        project.delete()
        messages.success(request, f"Project '{title}' was deleted.")
        return redirect("projects:dashboard")

    return render(
        request,
        "projects/project_confirm_delete.html",
        {"project": project},
    )


@login_required
def apply_to_project_view(request, pk):
    project = get_object_or_404(
        Project.objects.select_related("owner", "owner__profile"),
        pk=pk,
    )

    if request.method != "POST":
        return redirect("projects:project_detail", pk=pk)

    if project.owner == request.user:
        messages.error(request, "You cannot apply to join your own project.")
        return redirect("projects:project_detail", pk=pk)

    if project.status != Project.STATUS_OPEN:
        messages.error(request, "This project is closed and no longer accepting applications.")
        return redirect("projects:project_detail", pk=pk)

    if JoinRequest.objects.filter(project=project, applicant=request.user).exists():
        messages.warning(request, "You have already submitted a join request for this project.")
        return redirect("projects:project_detail", pk=pk)

    form = JoinRequestForm(request.POST)
    if form.is_valid():
        try:
            join_req = form.save(commit=False)
            join_req.project = project
            join_req.applicant = request.user
            join_req.save()

            # Notify the project owner via email if they have an email address on file
            if project.owner.email:
                manage_url = request.build_absolute_uri(reverse("projects:manage_requests"))
                applicant_name = request.user.profile.full_name or request.user.username
                send_mail(
                    subject=f"[TeamUp] New Join Request for '{project.title}'",
                    message=(
                        f"Hi {project.owner.profile.full_name or project.owner.username},\n\n"
                        f"{applicant_name} (@{request.user.username}) has applied to join "
                        f"your project '{project.title}'.\n\n"
                        f'Applicant Pitch:\n"{join_req.message}"\n\n'
                        f"Review and accept or reject this request here:\n{manage_url}\n\n"
                        f"— TeamUp CSE Collaboration Portal"
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[project.owner.email],
                    fail_silently=True,
                )

            messages.success(request, "Your join request has been sent to the project lead!")
        except IntegrityError:
            messages.warning(request, "You have already applied to this project.")
    else:
        for err in form.errors.get("message", []):
            messages.error(request, err)

    return redirect("projects:project_detail", pk=pk)


@login_required
def manage_requests_view(request):
    incoming_requests = (
        JoinRequest.objects.filter(project__owner=request.user)
        .select_related("project", "applicant", "applicant__profile")
        .prefetch_related("applicant__profile__skills", "project__skills_needed")
    )
    return render(
        request,
        "projects/manage_requests.html",
        {"incoming_requests": incoming_requests},
    )


@login_required
def handle_request_action_view(request, req_id, decision):
    if request.method != "POST":
        return redirect("projects:manage_requests")

    join_req = get_object_or_404(
        JoinRequest.objects.select_related(
            "project",
            "project__owner",
            "project__owner__profile",
            "applicant",
            "applicant__profile",
        ),
        pk=req_id,
    )
    project = join_req.project

    if project.owner != request.user:
        raise PermissionDenied("Only the project owner can manage team members and requests.")

    if decision not in ("accept", "reject", "remove"):
        messages.error(request, "Invalid action.")
        return redirect("projects:manage_requests")

    project_url = request.build_absolute_uri(
        reverse("projects:project_detail", args=[project.pk])
    )
    dashboard_url = request.build_absolute_uri(reverse("projects:dashboard"))
    owner_name = project.owner.profile.full_name or project.owner.username
    applicant_name = join_req.applicant.profile.full_name or join_req.applicant.username

    email_messages = []
    redirect_target = "projects:manage_requests"

    with transaction.atomic():
        if decision == "accept":
            join_req.status = JoinRequest.STATUS_ACCEPTED
            join_req.save(update_fields=["status"])

            if join_req.applicant.email:
                email_messages.append(
                    (
                        f"[TeamUp] Your application for '{project.title}' was Accepted",
                        (
                            f"Hi {applicant_name},\n\n"
                            f"Project Lead {owner_name} (@{project.owner.username}) has accepted your "
                            f"join request for '{project.title}'.\n\n"
                            f"Application Status: ACCEPTED\n\n"
                            f"Congratulations! You are now on the active team roster. Reach out to "
                            f"{project.owner.email or project.owner.username} to coordinate next steps.\n\n"
                            f"View project details: {project_url}\n\n"
                            f"— TeamUp CSE Collaboration Portal"
                        ),
                        settings.DEFAULT_FROM_EMAIL,
                        [join_req.applicant.email],
                    )
                )

            accepted_count = project.join_requests.filter(
                status=JoinRequest.STATUS_ACCEPTED
            ).count()
            total_roster = 1 + accepted_count

            if total_roster >= project.team_size_needed:
                project.status = Project.STATUS_CLOSED
                project.save(update_fields=["status"])

                remaining_pending = list(
                    project.join_requests.filter(status=JoinRequest.STATUS_PENDING)
                    .select_related("applicant", "applicant__profile")
                )

                if remaining_pending:
                    pending_ids = [r.pk for r in remaining_pending]
                    JoinRequest.objects.filter(pk__in=pending_ids).update(
                        status=JoinRequest.STATUS_REJECTED
                    )

                    for pending_req in remaining_pending:
                        if pending_req.applicant.email:
                            p_name = (
                                pending_req.applicant.profile.full_name
                                or pending_req.applicant.username
                            )
                            email_messages.append(
                                (
                                    f"[TeamUp] Update on your application for '{project.title}' (Team Full)",
                                    (
                                        f"Hi {p_name},\n\n"
                                        f"Thank you for applying to '{project.title}' led by {owner_name}.\n\n"
                                        f"The project has now reached its maximum team size of "
                                        f"{project.team_size_needed} members and has been marked as Closed. "
                                        f"As a result, remaining pending applications could not be accommodated.\n\n"
                                        f"Explore other open projects matched to your skills on your dashboard:\n"
                                        f"{dashboard_url}\n\n"
                                        f"— TeamUp CSE Collaboration Portal"
                                    ),
                                    settings.DEFAULT_FROM_EMAIL,
                                    [pending_req.applicant.email],
                                )
                            )

                messages.success(
                    request,
                    f"Accepted {join_req.applicant.username}! '{project.title}' has reached its full team size "
                    f"({total_roster}/{project.team_size_needed}) and was automatically marked as Closed.",
                )
            else:
                messages.success(
                    request,
                    f"Accepted {join_req.applicant.username} into '{project.title}' "
                    f"({total_roster}/{project.team_size_needed} members filled).",
                )

        elif decision == "reject":
            join_req.status = JoinRequest.STATUS_REJECTED
            join_req.save(update_fields=["status"])
            messages.info(
                request,
                f"Rejected request from {join_req.applicant.username} for '{project.title}'.",
            )
            if join_req.applicant.email:
                email_messages.append(
                    (
                        f"[TeamUp] Your application for '{project.title}' was Rejected",
                        (
                            f"Hi {applicant_name},\n\n"
                            f"Project Lead {owner_name} (@{project.owner.username}) has reviewed your "
                            f"join request for '{project.title}'.\n\n"
                            f"Application Status: NOT SELECTED\n\n"
                            f"Visit your dashboard to discover other recommended projects:\n"
                            f"{dashboard_url}\n\n"
                            f"— TeamUp CSE Collaboration Portal"
                        ),
                        settings.DEFAULT_FROM_EMAIL,
                        [join_req.applicant.email],
                    )
                )

        elif decision == "remove":
            if join_req.status != JoinRequest.STATUS_ACCEPTED:
                messages.warning(
                    request,
                    f"{join_req.applicant.username} is not currently an accepted member of this project.",
                )
                return redirect("projects:project_detail", pk=project.pk)

            # Update status to Rejected so the roster slot frees up while keeping record history
            join_req.status = JoinRequest.STATUS_REJECTED
            join_req.save(update_fields=["status"])

            accepted_count = project.join_requests.filter(
                status=JoinRequest.STATUS_ACCEPTED
            ).count()
            total_roster = 1 + accepted_count

            # Automatically reopen the project if it was Closed, has space, and deadline hasn't passed
            reopened = False
            if (
                project.status == Project.STATUS_CLOSED
                and total_roster < project.team_size_needed
                and project.deadline >= timezone.localdate()
            ):
                project.status = Project.STATUS_OPEN
                project.save(update_fields=["status"])
                reopened = True

            if join_req.applicant.email:
                email_messages.append(
                    (
                        f"[TeamUp] Roster update for '{project.title}'",
                        (
                            f"Hi {applicant_name},\n\n"
                            f"Project Lead {owner_name} (@{project.owner.username}) has removed you from "
                            f"the active team roster for '{project.title}'.\n\n"
                            f"You can browse and apply to other open projects on your dashboard:\n"
                            f"{dashboard_url}\n\n"
                            f"— TeamUp CSE Collaboration Portal"
                        ),
                        settings.DEFAULT_FROM_EMAIL,
                        [join_req.applicant.email],
                    )
                )

            if reopened:
                messages.info(
                    request,
                    f"Removed {join_req.applicant.username} from '{project.title}'. "
                    f"Because a spot opened up ({total_roster}/{project.team_size_needed}), "
                    f"the project was automatically reopened for applications.",
                )
            else:
                messages.info(
                    request,
                    f"Removed {join_req.applicant.username} from the roster "
                    f"({total_roster}/{project.team_size_needed} members filled).",
                )

            redirect_target = request.POST.get("next") or "projects:manage_requests"

    if email_messages:
        send_mass_mail(email_messages, fail_silently=True)

    if redirect_target == "project_detail":
        return redirect("projects:project_detail", pk=project.pk)
    return redirect("projects:manage_requests")


@login_required
def my_applications_view(request):
    applications = (
        JoinRequest.objects.filter(applicant=request.user)
        .select_related("project", "project__owner", "project__owner__profile")
        .prefetch_related("project__skills_needed")
    )
    return render(
        request,
        "projects/my_applications.html",
        {"applications": applications},
    )


@login_required
def withdraw_application_view(request, req_id):
    if request.method != "POST":
        return redirect("projects:my_applications")

    join_req = get_object_or_404(
        JoinRequest.objects.select_related(
            "project",
            "project__owner",
            "project__owner__profile",
            "applicant",
            "applicant__profile",
        ),
        pk=req_id,
    )

    if join_req.applicant != request.user:
        raise PermissionDenied("You can only withdraw your own project applications.")

    if join_req.status != JoinRequest.STATUS_PENDING:
        messages.error(
            request,
            f"Cannot withdraw your application for '{join_req.project.title}' "
            f"because it has already been {join_req.status.lower()}.",
        )
        return redirect("projects:my_applications")

    project = join_req.project
    applicant_name = request.user.profile.full_name or request.user.username
    owner_name = project.owner.profile.full_name or project.owner.username

    join_req.delete()

    # Notify the project owner via email that the pending application was withdrawn
    if project.owner.email:
        send_mail(
            subject=f"[TeamUp] Application withdrawn for '{project.title}'",
            message=(
                f"Hi {owner_name},\n\n"
                f"{applicant_name} (@{request.user.username}) has withdrawn their pending "
                f"join request for '{project.title}'.\n\n"
                f"— TeamUp CSE Collaboration Portal"
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[project.owner.email],
            fail_silently=True,
        )

    messages.info(
        request,
        f"Your pending application for '{project.title}' has been withdrawn.",
    )

    next_target = request.POST.get("next")
    if next_target == "project_detail":
        return redirect("projects:project_detail", pk=project.pk)
    return redirect("projects:my_applications")


@login_required
def dashboard_view(request):
    my_projects = attach_match_scores(
        Project.objects.filter(owner=request.user)
        .select_related("owner", "owner__profile")
        .prefetch_related("skills_needed")
        .annotate(
            pending_count=Count(
                "join_requests",
                filter=Q(join_requests__status=JoinRequest.STATUS_PENDING),
            ),
            accepted_count=Count(
                "join_requests",
                filter=Q(join_requests__status=JoinRequest.STATUS_ACCEPTED),
            ),
        ),
        request.user,
    )

    my_applications = (
        JoinRequest.objects.filter(applicant=request.user)
        .select_related("project", "project__owner")
        .order_by("-created_at")[:5]
    )

    pending_incoming = (
        JoinRequest.objects.filter(
            project__owner=request.user,
            status=JoinRequest.STATUS_PENDING,
        )
        .select_related("project", "applicant", "applicant__profile")
        .prefetch_related("applicant__profile__skills")
    )

    # Recommended open projects (excluding user's own and already applied) sorted by match score
    applied_project_ids = JoinRequest.objects.filter(
        applicant=request.user
    ).values_list("project_id", flat=True)

    candidate_projects = (
        Project.objects.filter(status=Project.STATUS_OPEN)
        .exclude(owner=request.user)
        .exclude(id__in=applied_project_ids)
        .select_related("owner", "owner__profile")
        .prefetch_related("skills_needed")
    )
    scored_candidates = attach_match_scores(candidate_projects, request.user)
    scored_candidates.sort(key=lambda p: (p.match_score, p.created_at), reverse=True)
    recommended_projects = scored_candidates[:4]

    # Retrieve recently viewed projects from session preserving visit order
    recent_ids = request.session.get("recently_viewed", [])
    recent_map = {
        p.id: p
        for p in Project.objects.filter(id__in=recent_ids)
        .select_related("owner", "owner__profile")
        .prefetch_related("skills_needed")
    }
    recently_viewed = []
    for pid in recent_ids:
        if pid in recent_map:
            proj = recent_map[pid]
            proj.match_score = proj.calculate_match_score(request.user)
            recently_viewed.append(proj)

    context = {
        "my_projects": my_projects,
        "my_applications": my_applications,
        "pending_incoming": pending_incoming,
        "recommended_projects": recommended_projects,
        "recently_viewed": recently_viewed,
    }
    return render(request, "projects/dashboard.html", context)


@login_required
def export_rosters_csv_view(request):
    """
    Allow Faculty group members, staff, or superusers to download a CSV
    of all projects and their accepted student rosters.
    """
    is_faculty_or_staff = (
        request.user.is_staff
        or request.user.is_superuser
        or request.user.groups.filter(name="Faculty").exists()
    )
    if not is_faculty_or_staff:
        raise PermissionDenied("Only Faculty coordinators and administrators can export project rosters.")

    queryset = Project.objects.all()

    category = request.GET.get("category", "").strip()
    status_filter = request.GET.get("status", "").strip()
    if category:
        queryset = queryset.filter(category=category)
    if status_filter in (Project.STATUS_OPEN, Project.STATUS_CLOSED):
        queryset = queryset.filter(status=status_filter)

    return generate_projects_roster_csv(queryset, filename_prefix="faculty_all_project_rosters")


@login_required
def faculty_analytics_view(request):
    """
    Staff/Faculty-only analytics dashboard demonstrating Django ORM aggregations:
    values(), annotate(), conditional Count(filter=Q(...)), and cross-model metrics.
    """
    is_faculty_or_staff = (
        request.user.is_staff
        or request.user.is_superuser
        or request.user.groups.filter(name="Faculty").exists()
    )
    if not is_faculty_or_staff:
        raise PermissionDenied(
            "Only Faculty coordinators and staff can view the department analytics dashboard."
        )

    # 1. Top-level KPI metrics
    total_projects = Project.objects.count()
    open_projects = Project.objects.filter(status=Project.STATUS_OPEN).count()
    closed_projects = Project.objects.filter(status=Project.STATUS_CLOSED).count()

    total_requests = JoinRequest.objects.count()
    accepted_requests = JoinRequest.objects.filter(
        status=JoinRequest.STATUS_ACCEPTED
    ).count()
    acceptance_rate = (
        round((accepted_requests / total_requests) * 100) if total_requests else 0
    )

    # Cross-year collaboration count: accepted requests where applicant's year != owner's year
    cross_year_collaborations = (
        JoinRequest.objects.filter(status=JoinRequest.STATUS_ACCEPTED)
        .exclude(
            applicant__profile__year_of_study=F(
                "project__owner__profile__year_of_study"
            )
        )
        .count()
    )

    # 2. Total Projects by Category (ORM values + annotate)
    raw_category_counts = (
        Project.objects.values("category")
        .annotate(
            total=Count("id"),
            open_count=Count("id", filter=Q(status=Project.STATUS_OPEN)),
            closed_count=Count("id", filter=Q(status=Project.STATUS_CLOSED)),
        )
        .order_by("-total")
    )

    counts_by_slug = {row["category"]: row for row in raw_category_counts}
    category_stats = []
    for slug, label in Project.CATEGORY_CHOICES:
        row = counts_by_slug.get(
            slug, {"total": 0, "open_count": 0, "closed_count": 0}
        )
        pct = round((row["total"] / total_projects) * 100) if total_projects else 0
        category_stats.append(
            {
                "slug": slug,
                "label": label,
                "total": row["total"],
                "open_count": row["open_count"],
                "closed_count": row["closed_count"],
                "percentage": pct,
            }
        )
    category_stats.sort(key=lambda item: item["total"], reverse=True)

    # 3. Most In-Demand Skills (Project demand vs. Student supply)
    skill_queryset = (
        Skill.objects.annotate(
            project_demand=Count("projects", distinct=True),
            student_supply=Count("profiles", distinct=True),
        )
        .filter(Q(project_demand__gt=0) | Q(student_supply__gt=0))
        .order_by("-project_demand", "-student_supply", "name")[:10]
    )

    max_demand = max((s.project_demand for s in skill_queryset), default=1) or 1
    skill_stats = []
    for s in skill_queryset:
        skill_stats.append(
            {
                "name": s.name,
                "slug": s.slug,
                "project_demand": s.project_demand,
                "student_supply": s.student_supply,
                "demand_bar_pct": round((s.project_demand / max_demand) * 100),
            }
        )

    # 4. Collaboration Rates Across Study Years (Years 1 to 4)
    year_stats = []
    for year_num, year_label in Profile.YEAR_CHOICES:
        profiles_in_year = Profile.objects.filter(year_of_study=year_num)
        total_students = profiles_in_year.count()

        projects_led = Project.objects.filter(
            owner__profile__year_of_study=year_num
        ).count()
        applications_sent = JoinRequest.objects.filter(
            applicant__profile__year_of_study=year_num
        ).count()
        accepted_spots = JoinRequest.objects.filter(
            applicant__profile__year_of_study=year_num,
            status=JoinRequest.STATUS_ACCEPTED,
        ).count()

        # Active collaborators: students in this year who either own a project or sent >=1 application
        active_students = (
            profiles_in_year.filter(
                Q(user__owned_projects__isnull=False)
                | Q(user__applications__isnull=False)
            )
            .distinct()
            .count()
        )
        participation_rate = (
            round((active_students / total_students) * 100)
            if total_students
            else 0
        )

        year_stats.append(
            {
                "year_num": year_num,
                "year_label": year_label,
                "total_students": total_students,
                "active_students": active_students,
                "projects_led": projects_led,
                "applications_sent": applications_sent,
                "accepted_spots": accepted_spots,
                "participation_rate": participation_rate,
            }
        )

    context = {
        "total_projects": total_projects,
        "open_projects": open_projects,
        "closed_projects": closed_projects,
        "total_requests": total_requests,
        "accepted_requests": accepted_requests,
        "acceptance_rate": acceptance_rate,
        "cross_year_collaborations": cross_year_collaborations,
        "category_stats": category_stats,
        "skill_stats": skill_stats,
        "year_stats": year_stats,
    }
    return render(request, "projects/faculty_analytics.html", context)


def api_open_projects_view(request):
    """
    Lightweight JSON API endpoint returning open projects, required skills,
    roster counts, and skill match scores (sorted by match_score descending).
    Supports optional GET filters: ?q=, ?category=, ?skill=
    """
    if request.method != "GET":
        return JsonResponse({"error": "Only GET requests are allowed."}, status=405)

    queryset = (
        Project.objects.filter(status=Project.STATUS_OPEN)
        .select_related("owner", "owner__profile")
        .prefetch_related("skills_needed")
        .annotate(
            accepted_count=Count(
                "join_requests",
                filter=Q(join_requests__status=JoinRequest.STATUS_ACCEPTED),
            )
        )
    )

    q = request.GET.get("q", "").strip()
    category = request.GET.get("category", "").strip()
    skill_slug = request.GET.get("skill", "").strip()

    if q:
        queryset = queryset.filter(
            Q(title__icontains=q) | Q(description__icontains=q)
        )
    if category:
        queryset = queryset.filter(category=category)
    if skill_slug:
        queryset = queryset.filter(skills_needed__slug=skill_slug)

    queryset = queryset.distinct().order_by("-created_at")

    if request.user.is_authenticated and hasattr(request.user, "profile"):
        request.user.profile.skills.all()  # warm prefetch cache

    projects_payload = []
    for project in queryset:
        owner_profile = getattr(project.owner, "profile", None)
        match_score = project.calculate_match_score(request.user)

        projects_payload.append(
            {
                "id": project.pk,
                "title": project.title,
                "description": project.description,
                "category": {
                    "slug": project.category,
                    "label": project.get_category_display(),
                },
                "status": project.status,
                "owner": {
                    "username": project.owner.username,
                    "full_name": (
                        owner_profile.full_name
                        if owner_profile and owner_profile.full_name
                        else project.owner.username
                    ),
                    "branch": owner_profile.branch if owner_profile else "CSE",
                    "year_of_study": (
                        owner_profile.year_of_study if owner_profile else None
                    ),
                },
                "skills_needed": [
                    {"name": s.name, "slug": s.slug}
                    for s in project.skills_needed.all()
                ],
                "team_size_filled": 1 + project.accepted_count,
                "team_size_needed": project.team_size_needed,
                "deadline": project.deadline.isoformat(),
                "match_score": match_score,
                "detail_url": request.build_absolute_uri(
                    reverse("projects:project_detail", args=[project.pk])
                ),
            }
        )

    # Sort highest skill match first when a student is logged in
    if request.user.is_authenticated:
        projects_payload.sort(key=lambda item: item["match_score"], reverse=True)

    return JsonResponse(
        {
            "authenticated": request.user.is_authenticated,
            "username": request.user.username if request.user.is_authenticated else None,
            "count": len(projects_payload),
            "projects": projects_payload,
        },
        json_dumps_params={"indent": 2},
    )


def custom_permission_denied_view(request, exception=None):
    return render(request, "403.html", {"exception": exception}, status=403)


def custom_page_not_found_view(request, exception=None):
    return render(request, "404.html", status=404)
