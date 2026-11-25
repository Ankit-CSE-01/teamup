from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User

from .models import Profile, Skill


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name", "slug")
    list_filter = ("name",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "full_name", "branch", "year_of_study", "github_url")
    list_filter = ("branch", "year_of_study", "skills")
    search_fields = ("user__username", "user__email", "full_name", "branch", "bio")
    filter_horizontal = ("skills",)


class CustomUserAdmin(BaseUserAdmin):
    """Restrict user deletion strictly to superusers; Faculty can inspect but not delete users."""

    def has_delete_permission(self, request, obj=None):
        if not request.user.is_superuser:
            return False
        return super().has_delete_permission(request, obj)


admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)
