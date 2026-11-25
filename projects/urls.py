from django.urls import path, re_path
from . import views

app_name = "projects"

urlpatterns = [
    path("", views.project_list_view, name="project_list"),
    path("dashboard/", views.dashboard_view, name="dashboard"),
    path("projects/create/", views.project_create_view, name="project_create"),
    path("projects/<int:pk>/", views.project_detail_view, name="project_detail"),
    path("projects/<int:pk>/edit/", views.project_edit_view, name="project_edit"),
    path("projects/<int:pk>/delete/", views.project_delete_view, name="project_delete"),
    path("projects/<int:pk>/apply/", views.apply_to_project_view, name="project_apply"),
    path(
        "projects/export/rosters-csv/",
        views.export_rosters_csv_view,
        name="export_rosters_csv",
    ),
    path("requests/manage/", views.manage_requests_view, name="manage_requests"),
    path(
        "requests/<int:req_id>/action/<str:decision>/",
        views.handle_request_action_view,
        name="handle_request_action",
    ),
    path("applications/mine/", views.my_applications_view, name="my_applications"),
    path(
        "applications/<int:req_id>/withdraw/",
        views.withdraw_application_view,
        name="withdraw_application",
    ),
    path(
        "analytics/faculty/",
        views.faculty_analytics_view,
        name="faculty_analytics",
    ),
    path(
        "api/projects/",
        views.api_open_projects_view,
        name="api_open_projects",
    ),
    # Unit II Requirement: re_path with regular expression capturing category slug
    re_path(
        r"^category/(?P<slug>[a-z-]+)/$",
        views.category_projects_view,
        name="category_projects",
    ),
]
