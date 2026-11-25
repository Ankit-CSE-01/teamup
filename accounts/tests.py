from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse

from .forms import ProfileForm, SignUpForm
from .models import Profile, Skill


class AccountsModelAndSignalTests(TestCase):
    def test_profile_auto_created_on_user_signup_signal(self):
        user = User.objects.create_user(username="test_student", password="password123")
        self.assertTrue(Profile.objects.filter(user=user).exists())
        self.assertEqual(user.profile.branch, "CSE")
        self.assertTrue(user.groups.filter(name="Students").exists())

    def test_skill_and_profile_str_representations(self):
        skill = Skill.objects.create(name="Django", slug="django")
        self.assertEqual(str(skill), "Django")
        user = User.objects.create_user(username="riya", password="password123")
        user.profile.full_name = "Riya Sen"
        user.profile.year_of_study = 3
        user.profile.save()
        self.assertEqual(str(user.profile), "Riya Sen (CSE - Year 3)")


class AccountsFormValidationTests(TestCase):
    def setUp(self):
        User.objects.create_user(
            username="existing",
            email="duplicate@univ.edu",
            password="password123",
        )

    def test_signup_form_rejects_duplicate_email(self):
        form = SignUpForm(
            data={
                "username": "new_user",
                "email": "DUPLICATE@univ.edu",
                "full_name": "New Student",
                "year_of_study": 2,
                "branch": "CSE",
                "password1": "StrongPass#2026",
                "password2": "StrongPass#2026",
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)

    def test_signup_form_valid_creates_user_and_updates_profile(self):
        form = SignUpForm(
            data={
                "username": "freshman",
                "email": "freshman@univ.edu",
                "full_name": "Freshman Kid",
                "year_of_study": 1,
                "branch": "CSE-AI",
                "password1": "StrongPass#2026",
                "password2": "StrongPass#2026",
            }
        )
        self.assertTrue(form.is_valid())
        user = form.save()
        self.assertEqual(user.profile.full_name, "Freshman Kid")
        self.assertEqual(user.profile.branch, "CSE-AI")

    def test_profile_form_validates_github_url_prefix(self):
        user = User.objects.create_user(username="dev1", password="password123")
        bad_form = ProfileForm(
            data={
                "full_name": "Dev One",
                "year_of_study": 2,
                "branch": "CSE",
                "github_url": "https://gitlab.com/dev1",
            },
            instance=user.profile,
        )
        self.assertFalse(bad_form.is_valid())
        self.assertIn("github_url", bad_form.errors)

        good_form = ProfileForm(
            data={
                "full_name": "Dev One",
                "year_of_study": 2,
                "branch": "CSE",
                "github_url": "https://github.com/dev1",
            },
            instance=user.profile,
        )
        self.assertTrue(good_form.is_valid())


class AccountsViewsAndCookiesTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="ishaan", password="password123")

    def test_profile_edit_requires_authentication_and_redirects_with_next(self):
        edit_url = reverse("accounts:profile_edit")
        response = self.client.get(edit_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(f"?next={edit_url}", response.url)

    def test_theme_toggle_sets_cookie(self):
        response = self.client.get(reverse("accounts:toggle_theme", args=["dark"]))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.cookies["theme"].value, "dark")

    def test_only_superuser_can_delete_users_in_admin(self):
        from django.contrib.admin.sites import AdminSite
        from .admin import CustomUserAdmin

        faculty = User.objects.create_user(
            username="faculty_staff", password="password123", is_staff=True
        )
        super_admin = User.objects.create_superuser(
            username="dean_root", email="root@univ.edu", password="password123"
        )
        user_admin = CustomUserAdmin(User, AdminSite())

        class DummyRequest:
            def __init__(self, u):
                self.user = u

        self.assertFalse(
            user_admin.has_delete_permission(DummyRequest(faculty), self.user)
        )
        self.assertTrue(
            user_admin.has_delete_permission(DummyRequest(super_admin), self.user)
        )

    def test_api_profile_detail_returns_profile_skills_and_owned_projects(self):
        from datetime import timedelta
        from django.utils import timezone
        from projects.models import Project

        skill_py = Skill.objects.create(name="Python", slug="python")
        skill_dj = Skill.objects.create(name="Django", slug="django")

        self.user.profile.full_name = "Ishaan Kapoor"
        self.user.profile.year_of_study = 3
        self.user.profile.branch = "CSE"
        self.user.profile.github_url = "https://github.com/ishaankapoor"
        self.user.profile.save()
        self.user.profile.skills.set([skill_py, skill_dj])

        proj = Project.objects.create(
            owner=self.user,
            title="AI Attendance System",
            description="Automated classroom attendance.",
            category=Project.CATEGORY_MINI,
            team_size_needed=3,
            deadline=timezone.localdate() + timedelta(days=20),
            status=Project.STATUS_OPEN,
        )
        proj.skills_needed.set([skill_py])

        url = reverse("accounts:api_profile_detail", args=[self.user.username])
        res = self.client.get(url)

        self.assertEqual(res.status_code, 200)
        self.assertEqual(res["Content-Type"], "application/json")

        data = res.json()
        self.assertEqual(data["username"], "ishaan")
        self.assertEqual(data["full_name"], "Ishaan Kapoor")
        self.assertEqual(data["year_of_study"]["number"], 3)
        self.assertEqual(len(data["skills"]), 2)
        self.assertEqual(data["owned_projects_count"], 1)
        self.assertEqual(data["owned_projects"][0]["title"], "AI Attendance System")

    def test_api_profile_detail_returns_404_for_missing_user_and_405_for_post(self):
        missing_url = reverse("accounts:api_profile_detail", args=["ghost_student"])
        res_404 = self.client.get(missing_url)
        self.assertEqual(res_404.status_code, 404)

        valid_url = reverse("accounts:api_profile_detail", args=[self.user.username])
        res_405 = self.client.post(valid_url)
        self.assertEqual(res_405.status_code, 405)

    def test_student_directory_requires_login(self):
        url = reverse("accounts:student_directory")
        res = self.client.get(url)
        self.assertEqual(res.status_code, 302)
        self.assertIn(f"?next={url}", res.url)

    def test_student_directory_filters_by_skill_branch_year_and_query(self):
        skill_flutter = Skill.objects.create(name="Flutter", slug="flutter")
        skill_rust = Skill.objects.create(name="Rust", slug="rust")

        self.user.profile.full_name = "Ishaan FlutterDev"
        self.user.profile.branch = "CSE-AI"
        self.user.profile.year_of_study = 3
        self.user.profile.save()
        self.user.profile.skills.set([skill_flutter])

        peer = User.objects.create_user(username="meera", password="password123")
        peer.profile.full_name = "Meera Systems"
        peer.profile.branch = "IT"
        peer.profile.year_of_study = 4
        peer.profile.save()
        peer.profile.skills.set([skill_rust])

        self.client.login(username="ishaan", password="password123")
        url = reverse("accounts:student_directory")

        # 1. Filter by skill=flutter
        res_skill = self.client.get(url, {"skill": "flutter"})
        self.assertEqual(res_skill.status_code, 200)
        self.assertContains(res_skill, "Ishaan FlutterDev")
        self.assertNotContains(res_skill, "Meera Systems")

        # 2. Filter by branch=IT and year=4
        res_branch_year = self.client.get(url, {"branch": "IT", "year": "4"})
        self.assertContains(res_branch_year, "Meera Systems")
        self.assertNotContains(res_branch_year, "Ishaan FlutterDev")

        # 3. Filter by keyword query
        res_q = self.client.get(url, {"q": "FlutterDev"})
        self.assertContains(res_q, "Ishaan FlutterDev")
        self.assertNotContains(res_q, "Meera Systems")

    def test_project_owner_can_invite_student_and_sends_email_with_apply_link(self):
        from datetime import timedelta
        from django.core import mail
        from django.utils import timezone
        from projects.models import Project

        skill_py = Skill.objects.create(name="Python", slug="python")
        skill_ml = Skill.objects.create(name="ML", slug="ml")

        owner = User.objects.create_user(
            username="lead_aarav",
            email="aarav@univ.edu",
            password="password123",
        )
        owner.profile.full_name = "Aarav Lead"
        owner.profile.save()

        self.user.email = "ishaan@univ.edu"
        self.user.save()
        self.user.profile.full_name = "Ishaan Candidate"
        self.user.profile.save()
        self.user.profile.skills.set([skill_py])

        project = Project.objects.create(
            owner=owner,
            title="Autonomous Rover AI",
            description="Rover navigation system.",
            category=Project.CATEGORY_HACKATHON,
            team_size_needed=4,
            deadline=timezone.localdate() + timedelta(days=14),
            status=Project.STATUS_OPEN,
        )
        project.skills_needed.set([skill_py, skill_ml])  # 50% match for Ishaan

        self.client.login(username="lead_aarav", password="password123")
        invite_url = reverse("accounts:invite_student", args=[self.user.username])
        res = self.client.post(
            invite_url,
            data={
                "project_id": project.pk,
                "note": "We need your Python skills for the rover control loop!",
            },
        )

        self.assertRedirects(
            res, reverse("accounts:profile_detail", args=[self.user.username])
        )
        self.assertEqual(len(mail.outbox), 1)

        sent = mail.outbox[0]
        self.assertEqual(sent.to, ["ishaan@univ.edu"])
        self.assertIn("invited you to join 'Autonomous Rover AI'", sent.subject)
        self.assertIn("Your Skill Match: 50%", sent.body)
        self.assertIn(
            "We need your Python skills for the rover control loop!", sent.body
        )
        self.assertIn(reverse("projects:project_detail", args=[project.pk]), sent.body)

    def test_non_owner_cannot_invite_student_to_someone_elses_project_returns_403(self):
        from datetime import timedelta
        from django.utils import timezone
        from projects.models import Project

        skill_py = Skill.objects.create(name="Python", slug="python")
        owner = User.objects.create_user(username="real_owner", password="password123")
        attacker = User.objects.create_user(username="attacker", password="password123")

        project = Project.objects.create(
            owner=owner,
            title="Owner Project",
            description="Description",
            category=Project.CATEGORY_MINI,
            team_size_needed=3,
            deadline=timezone.localdate() + timedelta(days=10),
            status=Project.STATUS_OPEN,
        )
        project.skills_needed.set([skill_py])

        self.client.login(username="attacker", password="password123")
        invite_url = reverse("accounts:invite_student", args=[self.user.username])
        res = self.client.post(invite_url, data={"project_id": project.pk})
        self.assertEqual(res.status_code, 403)
