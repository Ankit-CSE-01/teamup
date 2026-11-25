from datetime import timedelta
from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import Skill
from .forms import ProjectForm
from .models import JoinRequest, Project


class ProjectTestBase(TestCase):
    def setUp(self):
        self.skill_py = Skill.objects.create(name="Python", slug="python")
        self.skill_dj = Skill.objects.create(name="Django", slug="django")
        self.skill_ml = Skill.objects.create(name="ML", slug="ml")
        self.skill_react = Skill.objects.create(name="React", slug="react")

        self.owner = User.objects.create_user(
            username="owner_user",
            email="owner@univ.edu",
            password="password123",
        )
        self.applicant = User.objects.create_user(
            username="applicant_user",
            email="applicant@univ.edu",
            password="password123",
        )
        self.other = User.objects.create_user(
            username="other_user",
            password="password123",
        )

        self.applicant.profile.skills.set([self.skill_py, self.skill_dj])

        self.future_date = timezone.localdate() + timedelta(days=15)
        self.project = Project.objects.create(
            owner=self.owner,
            title="Campus Hackathon Portal",
            description="A Django portal for university hackathons.",
            category=Project.CATEGORY_HACKATHON,
            team_size_needed=4,
            deadline=self.future_date,
            status=Project.STATUS_OPEN,
        )
        self.project.skills_needed.set(
            [self.skill_py, self.skill_dj, self.skill_ml, self.skill_react]
        )


class SkillMatchScoreTests(ProjectTestBase):
    def test_match_score_calculation_partial_overlap(self):
        # Applicant has 2 of the 4 required skills -> 50%
        self.assertEqual(self.project.calculate_match_score(self.applicant), 50)

    def test_match_score_full_overlap(self):
        self.applicant.profile.skills.set(
            [self.skill_py, self.skill_dj, self.skill_ml, self.skill_react]
        )
        self.assertEqual(self.project.calculate_match_score(self.applicant), 100)

    def test_match_score_zero_when_no_overlap(self):
        self.assertEqual(self.project.calculate_match_score(self.other), 0)


class ProjectFormValidationTests(ProjectTestBase):
    def test_title_minimum_length_validation(self):
        form = ProjectForm(
            data={
                "title": "App",
                "description": "Valid description text here",
                "category": Project.CATEGORY_MINI,
                "skills_needed": [self.skill_py.id],
                "team_size_needed": 3,
                "deadline": self.future_date,
                "status": Project.STATUS_OPEN,
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("title", form.errors)

    def test_deadline_must_be_in_future(self):
        past_date = timezone.localdate() - timedelta(days=2)
        form = ProjectForm(
            data={
                "title": "Valid Project Title",
                "description": "Valid description text",
                "category": Project.CATEGORY_MINI,
                "skills_needed": [self.skill_py.id],
                "team_size_needed": 3,
                "deadline": past_date,
                "status": Project.STATUS_OPEN,
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("deadline", form.errors)

    def test_team_size_between_2_and_10(self):
        form_too_small = ProjectForm(
            data={
                "title": "Solo Project Attempt",
                "description": "Valid description",
                "category": Project.CATEGORY_MINI,
                "skills_needed": [self.skill_py.id],
                "team_size_needed": 1,
                "deadline": self.future_date,
                "status": Project.STATUS_OPEN,
            }
        )
        self.assertFalse(form_too_small.is_valid())
        self.assertIn("team_size_needed", form_too_small.errors)

        form_too_large = ProjectForm(
            data={
                "title": "Huge Crowd Project",
                "description": "Valid description",
                "category": Project.CATEGORY_MINI,
                "skills_needed": [self.skill_py.id],
                "team_size_needed": 15,
                "deadline": self.future_date,
                "status": Project.STATUS_OPEN,
            }
        )
        self.assertFalse(form_too_large.is_valid())
        self.assertIn("team_size_needed", form_too_large.errors)


class ProjectAccessControlAndViewsTests(ProjectTestBase):
    def test_anonymous_user_redirected_on_create_project(self):
        url = reverse("projects:project_create")
        res = self.client.get(url)
        self.assertEqual(res.status_code, 302)
        self.assertIn(f"?next={url}", res.url)

    def test_non_owner_gets_403_on_edit_and_delete(self):
        self.client.login(username="other_user", password="password123")
        edit_res = self.client.get(reverse("projects:project_edit", args=[self.project.pk]))
        self.assertEqual(edit_res.status_code, 403)

        del_res = self.client.post(reverse("projects:project_delete", args=[self.project.pk]))
        self.assertEqual(del_res.status_code, 403)

    def test_owner_can_edit_and_delete_project(self):
        self.client.login(username="owner_user", password="password123")
        edit_res = self.client.post(
            reverse("projects:project_edit", args=[self.project.pk]),
            data={
                "title": "Updated Hackathon Portal",
                "description": "Updated description",
                "category": Project.CATEGORY_HACKATHON,
                "skills_needed": [self.skill_py.id, self.skill_dj.id],
                "team_size_needed": 5,
                "deadline": self.future_date,
                "status": Project.STATUS_OPEN,
            },
        )
        self.assertEqual(edit_res.status_code, 302)
        self.project.refresh_from_db()
        self.assertEqual(self.project.title, "Updated Hackathon Portal")

    def test_regex_category_route_filters_projects(self):
        url = reverse("projects:category_projects", kwargs={"slug": "hackathon"})
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Campus Hackathon Portal")

    def test_recently_viewed_stored_in_session_up_to_5(self):
        self.client.login(username="applicant_user", password="password123")
        res = self.client.get(reverse("projects:project_detail", args=[self.project.pk]))
        self.assertEqual(res.status_code, 200)
        self.assertIn(self.project.pk, self.client.session.get("recently_viewed", []))

    def test_regular_student_cannot_export_rosters_csv_returns_403(self):
        self.client.login(username="applicant_user", password="password123")
        url = reverse("projects:export_rosters_csv")
        res = self.client.get(url)
        self.assertEqual(res.status_code, 403)

    def test_faculty_user_can_export_rosters_csv_with_accepted_members(self):
        from django.contrib.auth.models import Group

        faculty_user = User.objects.create_user(
            username="prof_kumar",
            email="kumar@univ.edu",
            password="password123",
            is_staff=True,
        )
        faculty_group, _ = Group.objects.get_or_create(name="Faculty")
        faculty_user.groups.add(faculty_group)

        self.applicant.profile.full_name = "Aarav Applicant"
        self.applicant.profile.save()

        JoinRequest.objects.create(
            project=self.project,
            applicant=self.applicant,
            message="Ready to build!",
            status=JoinRequest.STATUS_ACCEPTED,
        )

        self.client.login(username="prof_kumar", password="password123")
        url = reverse("projects:export_rosters_csv")
        res = self.client.get(url)

        self.assertEqual(res.status_code, 200)
        self.assertIn("text/csv", res["Content-Type"])
        self.assertIn("attachment; filename=", res["Content-Disposition"])

        csv_content = res.content.decode("utf-8")
        self.assertIn("Campus Hackathon Portal", csv_content)
        self.assertIn("Aarav Applicant (@applicant_user", csv_content)

    def test_admin_bulk_action_exports_selected_projects_csv(self):
        from django.contrib.admin.sites import AdminSite
        from .admin import ProjectAdmin, export_selected_projects_csv

        faculty_user = User.objects.create_user(
            username="admin_faculty",
            password="password123",
            is_staff=True,
        )
        model_admin = ProjectAdmin(Project, AdminSite())

        class DummyRequest:
            def __init__(self, u):
                self.user = u

        queryset = Project.objects.filter(pk=self.project.pk)
        res = export_selected_projects_csv(model_admin, DummyRequest(faculty_user), queryset)

        self.assertEqual(res.status_code, 200)
        self.assertIn("text/csv", res["Content-Type"])
        csv_content = res.content.decode("utf-8")
        self.assertIn("Campus Hackathon Portal", csv_content)

    def test_regular_student_cannot_view_faculty_analytics_returns_403(self):
        self.client.login(username="applicant_user", password="password123")
        res = self.client.get(reverse("projects:faculty_analytics"))
        self.assertEqual(res.status_code, 403)

    def test_faculty_can_view_analytics_with_category_skill_and_year_metrics(self):
        from django.contrib.auth.models import Group

        # Set owner as 3rd Year and applicant as 2nd Year to test cross-year metric
        self.owner.profile.year_of_study = 3
        self.owner.profile.save()
        self.applicant.profile.year_of_study = 2
        self.applicant.profile.save()

        JoinRequest.objects.create(
            project=self.project,
            applicant=self.applicant,
            message="Joining across years!",
            status=JoinRequest.STATUS_ACCEPTED,
        )

        faculty_user = User.objects.create_user(
            username="prof_analytics",
            password="password123",
            is_staff=True,
        )
        faculty_group, _ = Group.objects.get_or_create(name="Faculty")
        faculty_user.groups.add(faculty_group)

        self.client.login(username="prof_analytics", password="password123")
        res = self.client.get(reverse("projects:faculty_analytics"))

        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context["total_projects"], 1)
        self.assertEqual(res.context["accepted_requests"], 1)
        self.assertEqual(res.context["cross_year_collaborations"], 1)

        # Verify top category is Hackathon with count 1
        top_category = res.context["category_stats"][0]
        self.assertEqual(top_category["slug"], Project.CATEGORY_HACKATHON)
        self.assertEqual(top_category["total"], 1)

        # Verify year_stats has all 4 academic years
        self.assertEqual(len(res.context["year_stats"]), 4)

    def test_json_api_returns_open_projects_skills_and_match_scores(self):
        # Create a Closed project to verify it is excluded from the open projects API
        closed_proj = Project.objects.create(
            owner=self.owner,
            title="Closed Legacy Project",
            description="Already finished.",
            category=Project.CATEGORY_MINI,
            team_size_needed=3,
            deadline=self.future_date,
            status=Project.STATUS_CLOSED,
        )
        closed_proj.skills_needed.set([self.skill_py])

        self.client.login(username="applicant_user", password="password123")
        res = self.client.get(reverse("projects:api_open_projects"))

        self.assertEqual(res.status_code, 200)
        self.assertEqual(res["Content-Type"], "application/json")

        payload = res.json()
        self.assertTrue(payload["authenticated"])
        self.assertEqual(payload["count"], 1)

        proj_data = payload["projects"][0]
        self.assertEqual(proj_data["title"], "Campus Hackathon Portal")
        self.assertEqual(proj_data["match_score"], 50)
        skill_slugs = [s["slug"] for s in proj_data["skills_needed"]]
        self.assertIn("python", skill_slugs)
        self.assertIn("django", skill_slugs)

    def test_json_api_filters_by_skill_and_rejects_post(self):
        url = reverse("projects:api_open_projects")
        res_filtered = self.client.get(url, {"skill": "nonexistent-skill"})
        self.assertEqual(res_filtered.status_code, 200)
        self.assertEqual(res_filtered.json()["count"], 0)

        res_post = self.client.post(url)
        self.assertEqual(res_post.status_code, 405)


class JoinRequestRulesTests(ProjectTestBase):
    def test_applicant_can_apply_and_duplicate_request_is_prevented(self):
        self.client.login(username="applicant_user", password="password123")
        apply_url = reverse("projects:project_apply", args=[self.project.pk])

        res1 = self.client.post(
            apply_url,
            data={"message": "I have built 3 Django apps and would love to help!"},
        )
        self.assertEqual(res1.status_code, 302)
        self.assertEqual(JoinRequest.objects.count(), 1)

        # Second attempt should not create a duplicate record
        res2 = self.client.post(
            apply_url,
            data={"message": "Trying to apply a second time to the same project."},
        )
        self.assertEqual(res2.status_code, 302)
        self.assertEqual(JoinRequest.objects.count(), 1)

    def test_owner_cannot_apply_to_own_project(self):
        self.client.login(username="owner_user", password="password123")
        apply_url = reverse("projects:project_apply", args=[self.project.pk])
        self.client.post(
            apply_url,
            data={"message": "Applying to my own project should be blocked."},
        )
        self.assertEqual(JoinRequest.objects.count(), 0)

    def test_cannot_apply_to_closed_project(self):
        self.project.status = Project.STATUS_CLOSED
        self.project.save()

        self.client.login(username="applicant_user", password="password123")
        apply_url = reverse("projects:project_apply", args=[self.project.pk])
        self.client.post(
            apply_url,
            data={"message": "Applying to a closed project should be rejected."},
        )
        self.assertEqual(JoinRequest.objects.count(), 0)

    def test_owner_can_accept_join_request_and_non_owner_gets_403(self):
        jr = JoinRequest.objects.create(
            project=self.project,
            applicant=self.applicant,
            message="Ready to contribute to the backend!",
        )
        action_url = reverse("projects:handle_request_action", args=[jr.pk, "accept"])

        # Non-owner gets 403
        self.client.login(username="other_user", password="password123")
        res_forbidden = self.client.post(action_url)
        self.assertEqual(res_forbidden.status_code, 403)

        # Owner succeeds
        self.client.login(username="owner_user", password="password123")
        res_ok = self.client.post(action_url)
        self.assertEqual(res_ok.status_code, 302)
        jr.refresh_from_db()
        self.assertEqual(jr.status, JoinRequest.STATUS_ACCEPTED)

    def test_dashboard_recommended_projects_sorted_by_match_score(self):
        low_match_proj = Project.objects.create(
            owner=self.owner,
            title="Pure React Native App",
            description="Only needs React.",
            category=Project.CATEGORY_MINI,
            team_size_needed=3,
            deadline=self.future_date,
            status=Project.STATUS_OPEN,
        )
        low_match_proj.skills_needed.set([self.skill_react])  # 0% for applicant

        self.client.login(username="applicant_user", password="password123")
        res = self.client.get(reverse("projects:dashboard"))
        self.assertEqual(res.status_code, 200)
        recommended = res.context["recommended_projects"]
        self.assertGreaterEqual(len(recommended), 2)
        self.assertEqual(recommended[0], self.project)  # 50% comes before 0%

    def test_accepting_join_request_sends_email_to_applicant(self):
        jr = JoinRequest.objects.create(
            project=self.project,
            applicant=self.applicant,
            message="I can build the backend APIs and write tests.",
        )
        self.client.login(username="owner_user", password="password123")
        action_url = reverse("projects:handle_request_action", args=[jr.pk, "accept"])
        res = self.client.post(action_url)

        self.assertEqual(res.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        sent_email = mail.outbox[0]
        self.assertIn("was Accepted", sent_email.subject)
        self.assertEqual(sent_email.to, ["applicant@univ.edu"])
        self.assertIn("Application Status: ACCEPTED", sent_email.body)

    def test_rejecting_join_request_sends_email_to_applicant(self):
        jr = JoinRequest.objects.create(
            project=self.project,
            applicant=self.applicant,
            message="Interested in helping with the project.",
        )
        self.client.login(username="owner_user", password="password123")
        action_url = reverse("projects:handle_request_action", args=[jr.pk, "reject"])
        res = self.client.post(action_url)

        self.assertEqual(res.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        sent_email = mail.outbox[0]
        self.assertIn("was Rejected", sent_email.subject)
        self.assertEqual(sent_email.to, ["applicant@univ.edu"])
        self.assertIn("Application Status: NOT SELECTED", sent_email.body)

    def test_project_auto_closes_and_emails_pending_applicants_when_team_size_reached(self):
        # Set team_size_needed to 2 (1 Owner + 1 Accepted Applicant fills the team)
        self.project.team_size_needed = 2
        self.project.save()

        self.other.email = "other@univ.edu"
        self.other.save()

        req_winner = JoinRequest.objects.create(
            project=self.project,
            applicant=self.applicant,
            message="I can take lead on the Django models.",
        )
        req_waitlist = JoinRequest.objects.create(
            project=self.project,
            applicant=self.other,
            message="I would also like to join this project.",
        )

        self.client.login(username="owner_user", password="password123")
        action_url = reverse("projects:handle_request_action", args=[req_winner.pk, "accept"])
        res = self.client.post(action_url)

        self.assertEqual(res.status_code, 302)

        # 1. Verify project status automatically flipped to Closed
        self.project.refresh_from_db()
        self.assertEqual(self.project.status, Project.STATUS_CLOSED)

        # 2. Verify winner is Accepted and remaining pending applicant is auto-Rejected
        req_winner.refresh_from_db()
        req_waitlist.refresh_from_db()
        self.assertEqual(req_winner.status, JoinRequest.STATUS_ACCEPTED)
        self.assertEqual(req_waitlist.status, JoinRequest.STATUS_REJECTED)

        # 3. Verify 2 emails were sent (1 acceptance + 1 team-full notification)
        self.assertEqual(len(mail.outbox), 2)
        recipients = [email.to[0] for email in mail.outbox]
        self.assertIn("applicant@univ.edu", recipients)
        self.assertIn("other@univ.edu", recipients)

        waitlist_email = next(e for e in mail.outbox if e.to == ["other@univ.edu"])
        self.assertIn("Team Full", waitlist_email.subject)
        self.assertIn("reached its maximum team size of 2 members", waitlist_email.body)

    def test_owner_can_remove_accepted_member_and_auto_reopen_closed_project(self):
        # Configure a full, closed project (team_size_needed = 2: 1 owner + 1 accepted member)
        self.project.team_size_needed = 2
        self.project.status = Project.STATUS_CLOSED
        self.project.save()

        accepted_req = JoinRequest.objects.create(
            project=self.project,
            applicant=self.applicant,
            message="Excited to work on this!",
            status=JoinRequest.STATUS_ACCEPTED,
        )

        self.client.login(username="owner_user", password="password123")
        remove_url = reverse("projects:handle_request_action", args=[accepted_req.pk, "remove"])
        res = self.client.post(remove_url, data={"next": "project_detail"})

        self.assertRedirects(res, reverse("projects:project_detail", args=[self.project.pk]))

        # 1. Verify JoinRequest is now marked Rejected
        accepted_req.refresh_from_db()
        self.assertEqual(accepted_req.status, JoinRequest.STATUS_REJECTED)

        # 2. Verify Project automatically reopened because a spot freed up and deadline is in future
        self.project.refresh_from_db()
        self.assertEqual(self.project.status, Project.STATUS_OPEN)

        # 3. Verify removal email was sent to the student
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["applicant@univ.edu"])
        self.assertIn("removed you from the active team roster", mail.outbox[0].body)

    def test_non_owner_cannot_remove_roster_member_returns_403(self):
        accepted_req = JoinRequest.objects.create(
            project=self.project,
            applicant=self.applicant,
            message="On the team!",
            status=JoinRequest.STATUS_ACCEPTED,
        )
        self.client.login(username="other_user", password="password123")
        remove_url = reverse("projects:handle_request_action", args=[accepted_req.pk, "remove"])
        res = self.client.post(remove_url)
        self.assertEqual(res.status_code, 403)

    def test_applicant_can_withdraw_own_pending_request(self):
        jr = JoinRequest.objects.create(
            project=self.project,
            applicant=self.applicant,
            message="I would like to join this hackathon team.",
            status=JoinRequest.STATUS_PENDING,
        )
        self.client.login(username="applicant_user", password="password123")
        withdraw_url = reverse("projects:withdraw_application", args=[jr.pk])
        res = self.client.post(withdraw_url)

        self.assertRedirects(res, reverse("projects:my_applications"))
        self.assertFalse(JoinRequest.objects.filter(pk=jr.pk).exists())
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["owner@univ.edu"])
        self.assertIn("withdrawn their pending join request", mail.outbox[0].body)

    def test_applicant_cannot_withdraw_accepted_or_rejected_request(self):
        jr = JoinRequest.objects.create(
            project=self.project,
            applicant=self.applicant,
            message="Already accepted member.",
            status=JoinRequest.STATUS_ACCEPTED,
        )
        self.client.login(username="applicant_user", password="password123")
        withdraw_url = reverse("projects:withdraw_application", args=[jr.pk])
        res = self.client.post(withdraw_url)

        self.assertRedirects(res, reverse("projects:my_applications"))
        # Record must remain in the database
        self.assertTrue(
            JoinRequest.objects.filter(pk=jr.pk, status=JoinRequest.STATUS_ACCEPTED).exists()
        )

    def test_other_user_cannot_withdraw_someone_elses_request_returns_403(self):
        jr = JoinRequest.objects.create(
            project=self.project,
            applicant=self.applicant,
            message="Pending application.",
            status=JoinRequest.STATUS_PENDING,
        )
        self.client.login(username="other_user", password="password123")
        withdraw_url = reverse("projects:withdraw_application", args=[jr.pk])
        res = self.client.post(withdraw_url)
        self.assertEqual(res.status_code, 403)
        self.assertTrue(JoinRequest.objects.filter(pk=jr.pk).exists())


class CustomTemplateFilterTests(ProjectTestBase):
    def test_days_until_filter_calculates_accurate_delta(self):
        from projects.templatetags.project_extras import days_until

        today = timezone.localdate()
        self.assertEqual(days_until(today + timedelta(days=10)), 10)
        self.assertEqual(days_until(today), 0)
        self.assertEqual(days_until(today - timedelta(days=3)), -3)

    def test_deadline_badge_filter_outputs_correct_urgency_classes(self):
        from projects.templatetags.project_extras import deadline_badge

        today = timezone.localdate()

        # 1. More than 5 days left -> deadline-normal
        badge_normal = str(deadline_badge(today + timedelta(days=12), "Open"))
        self.assertIn("deadline-normal", badge_normal)
        self.assertIn("12d left", badge_normal)

        # 2. 1 to 5 days left -> deadline-soon ('Closing Soon')
        badge_soon = str(deadline_badge(today + timedelta(days=3), "Open"))
        self.assertIn("deadline-soon", badge_soon)
        self.assertIn("Closing Soon", badge_soon)
        self.assertIn("3d left", badge_soon)

        # 3. Due today (0 days) -> deadline-urgent ('Closing Today!')
        badge_today = str(deadline_badge(today, "Open"))
        self.assertIn("deadline-urgent", badge_today)
        self.assertIn("Closing Today!", badge_today)

        # 4. Past deadline -> deadline-urgent ('Deadline Passed')
        badge_past = str(deadline_badge(today - timedelta(days=2), "Open"))
        self.assertIn("deadline-urgent", badge_past)
        self.assertIn("Deadline Passed", badge_past)

        # 5. Closed project overrides countdown
        badge_closed = str(deadline_badge(today + timedelta(days=10), "Closed"))
        self.assertIn("deadline-closed", badge_closed)

    def test_project_list_template_renders_custom_deadline_badge(self):
        res = self.client.get(reverse("projects:project_list"))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "15d left")
