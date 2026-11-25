import csv
from django.contrib import admin
from django.http import HttpResponse
from django.utils import timezone

from .models import JoinRequest, Project


def generate_projects_roster_csv(queryset, filename_prefix="teamup_project_rosters"):
    """
    Build and return an HttpResponse containing a CSV of the given Project queryset,
    including project metadata, required skills, lead details, and accepted teammates.
    """
    timestamp = timezone.localdate().strftime("%Y-%m-%d")
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = (
        f'attachment; filename="{filename_prefix}_{timestamp}.csv"'
    )

    writer = csv.writer(response)
    writer.writerow(
        [
            "Project ID",
            "Title",
            "Category",
            "Status",
            "Lead Name",
            "Lead Username",
            "Lead Email",
            "Lead Branch & Year",
            "Team Size Filled",
            "Team Size Needed",
            "Required Skills",
            "Accepted Roster Members (Name | Username | Branch | Year)",
            "Deadline",
            "Created At",
        ]
    )

    optimized_qs = queryset.select_related(
        "owner", "owner__profile"
    ).prefetch_related(
        "skills_needed",
        "join_requests__applicant__profile",
    )

    for project in optimized_qs:
        owner_profile = getattr(project.owner, "profile", None)
        lead_name = (
            owner_profile.full_name
            if owner_profile and owner_profile.full_name
            else project.owner.username
        )
        lead_branch_year = (
            f"{owner_profile.branch} (Year {owner_profile.year_of_study})"
            if owner_profile
            else "N/A"
        )

        skills_str = ", ".join(s.name for s in project.skills_needed.all())

        accepted_reqs = [
            req
            for req in project.join_requests.all()
            if req.status == JoinRequest.STATUS_ACCEPTED
        ]
        roster_entries = []
        for req in accepted_reqs:
            ap_prof = getattr(req.applicant, "profile", None)
            ap_name = (
                ap_prof.full_name
                if ap_prof and ap_prof.full_name
                else req.applicant.username
            )
            ap_branch = ap_prof.branch if ap_prof else "CSE"
            ap_year = f"Y{ap_prof.year_of_study}" if ap_prof else ""
            roster_entries.append(
                f"{ap_name} (@{req.applicant.username} | {ap_branch} {ap_year})"
            )

        roster_str = "; ".join(roster_entries) if roster_entries else "No additional members yet"
        total_filled = 1 + len(accepted_reqs)

        writer.writerow(
            [
                project.pk,
                project.title,
                project.get_category_display(),
                project.status,
                lead_name,
                project.owner.username,
                project.owner.email,
                lead_branch_year,
                total_filled,
                project.team_size_needed,
                skills_str,
                roster_str,
                project.deadline.strftime("%Y-%m-%d"),
                project.created_at.strftime("%Y-%m-%d %H:%M"),
            ]
        )

    return response


@admin.action(
    description="Export selected projects & accepted team rosters to CSV",
    permissions=["view"],
)
def export_selected_projects_csv(modeladmin, request, queryset):
    return generate_projects_roster_csv(queryset, filename_prefix="selected_project_rosters")


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "owner",
        "category",
        "team_size_needed",
        "status",
        "deadline",
        "created_at",
    )
    list_filter = ("category", "status", "skills_needed", "created_at")
    search_fields = ("title", "description", "owner__username", "owner__email")
    filter_horizontal = ("skills_needed",)
    date_hierarchy = "created_at"
    actions = [export_selected_projects_csv]


@admin.register(JoinRequest)
class JoinRequestAdmin(admin.ModelAdmin):
    list_display = ("project", "applicant", "status", "created_at")
    list_filter = ("status", "created_at", "project__category")
    search_fields = (
        "project__title",
        "applicant__username",
        "applicant__email",
        "message",
    )
