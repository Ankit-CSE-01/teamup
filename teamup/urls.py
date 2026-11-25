from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls", namespace="accounts")),
    path("", include("projects.urls", namespace="projects")),
]

handler403 = "projects.views.custom_permission_denied_view"
handler404 = "projects.views.custom_page_not_found_view"
