from django.urls import path
from . import views

app_name = "accounts"

urlpatterns = [
    path("signup/", views.signup_view, name="signup"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("directory/", views.student_directory_view, name="student_directory"),
    path("profile/edit/", views.profile_edit_view, name="profile_edit"),
    path("profile/<str:username>/", views.profile_detail_view, name="profile_detail"),
    path(
        "profile/<str:username>/invite/",
        views.invite_student_to_project_view,
        name="invite_student",
    ),
    path(
        "api/profile/<str:username>/",
        views.api_profile_detail_view,
        name="api_profile_detail",
    ),
    path("theme/<str:mode>/", views.toggle_theme_view, name="toggle_theme"),
]
