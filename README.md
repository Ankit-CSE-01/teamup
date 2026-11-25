# TeamUp — University Project & Hackathon Teammate Matchmaking Platform

**Course:** INT253 — Web Development in Python using Django

TeamUp solves a real discovery problem in Computer Science & Engineering (CSE) departments: students looking for teammates for Smart India Hackathon, course mini-projects, final-year capstones, research papers, and campus startups no longer have to rely on scattered WhatsApp forwards. Students build a skill-tagged profile, discover projects ranked by percentage skill overlap, search a peer directory, invite teammates, and manage join requests in one place—while Faculty coordinators get analytics dashboards and CSV roster exports.

---

## Quick Setup & Run Instructions

```bash
# 1. Create and activate a Python virtual environment
python3 -m venv venv
source venv/bin/activate        # On Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Apply database migrations
python manage.py migrate

# 4. Seed 15 skills, Faculty/Students groups, 8 demo users, 12 projects, and join requests
python manage.py seed_demo

# 5. (Optional) Create an interactive superuser for Django Admin
python manage.py createsuperuser

# 6. Run the automated test suite (48 unit tests)
python manage.py test -v 2

# 7. Start the development server
python manage.py runserver
```

Open `http://127.0.0.1:8000/` in your browser.

- **Demo Student Login:** `aarav_sharma` / `teamup123` (or `priya_nair`, `rohan_verma`, `sneha_reddy`, `kabir_khan`, `anya_gupta`, `vikram_singh`)
- **Demo Faculty Login:** `prof_mehta` / `teamup123`

---

## Core & Extended Features

1. **Authentication & Student Profiles:** Signup (unique email validation), login with `?next=` redirect, logout, auto-created `Profile` via `post_save` signal, skill tagging, and GitHub URL validation (`https://github.com/`).
2. **Project CRUD & Ownership Controls:** Create, edit, and delete projects with validation (future deadline, team size 2–10, title ≥ 5 chars). Non-owners receive `403 Forbidden`.
3. **Browse, Search, Regex Category Routes & Custom Template Filters:** Filter by keyword, category, skill, and status with pagination, `^category/(?P<slug>[a-z-]+)/$` regex routes, and custom `deadline_badge` / `days_until` template filters.
4. **Join Requests, Auto-Close, Roster Removal & Withdrawal:**
   - Apply with a pitch (no self-applying, no duplicates, no closed projects).
   - Console email notifications on apply, accept, reject, auto-close waitlist rejection, member removal, application withdrawal, and project invitations.
   - Atomic auto-close when `1 (owner) + accepted == team_size_needed`, automatically rejecting and emailing remaining pending applicants.
   - Owner can remove an accepted roster member (auto-reopening the project if previously closed and deadline is in the future).
   - Applicants can withdraw their own `Pending` requests.
5. **Skill Match Engine & Dashboard:** Percentage overlap score on cards, "Recommended For You" sorted by match score, pending requests, my projects, my applications, and session-backed "Recently Viewed Projects" (last 5).
6. **Student Directory & Project Invitations:** Searchable/filterable Student Directory (`/accounts/directory/`) by keyword, skill, branch, and study year, plus "Invite to Project" email invitations from any peer's profile page.
7. **Faculty Analytics & CSV Roster Export:** Staff/Faculty-only Analytics Dashboard (`/analytics/faculty/`) with KPIs, category distribution, skill demand vs. supply, and cross-year participation rates; plus CSV roster exports via `/projects/export/rosters-csv/` and a Django Admin bulk action.
8. **Lightweight JSON API Endpoints:**
   - `GET /api/projects/` — open projects, required skills, roster counts, and personalized match scores.
   - `GET /accounts/api/profile/<username>/` — student public profile, skills, and owned projects.
9. **Cookie-Backed Theme Switcher & Custom Error Pages:** Light/Dark theme saved in a 30-day cookie, custom `403.html` and `404.html` pages, and Django messages feedback.

---

## Entity-Relationship (ER) Architecture

1. **User (Django Auth) 1 —— 1 Profile (`accounts.Profile`)**
   - `OneToOneField(related_name="profile")`, auto-created via a `post_save` signal on `User`.
   - Stores `full_name`, `year_of_study` (1–4), `branch` (default `"CSE"`), `bio`, `github_url`.
2. **Profile M —— N Skill (`accounts.Skill`)**
   - `ManyToManyField(related_name="profiles")`. Represents the student's technical competencies.
3. **User 1 —— N Project (`projects.Project`)**
   - `ForeignKey(related_name="owned_projects")`. Stores `title`, `description`, `category`, `team_size_needed`, `deadline`, `status`, `created_at`.
4. **Project M —— N Skill (`accounts.Skill`)**
   - `ManyToManyField(related_name="projects")`. Used alongside `Profile.skills` to compute the percentage overlap match score.
5. **Project 1 —— N JoinRequest N —— 1 User (`projects.JoinRequest`)**
   - Connects an `applicant` (`User`) to a `Project` with `message`, `status` (`Pending`/`Accepted`/`Rejected`), and a database-level `UniqueConstraint(fields=["project", "applicant"])`.

---

## INT253 Syllabus Unit Mapping

| Syllabus Unit | Core Concept | Where It Is Demonstrated in TeamUp |
|---|---|---|
| **Unit I: Django Fundamentals & Project Setup** | Apps, settings configuration, static files, management commands, console email backend | `teamup/settings.py`, `accounts` & `projects` apps, `seed_demo.py` |
| **Unit II: URLs & Function-Based Views** | `path()` converters (`<int:pk>`, `<str:username>`), `re_path()` regex (`^category/(?P<slug>[a-z-]+)/$`), namespaces, `@login_required`, `JsonResponse`, CSV `HttpResponse` | `teamup/urls.py`, `accounts/urls.py`, `projects/urls.py`, `projects/views.py`, `accounts/views.py` |
| **Unit III: Django Template Language (DTL)** | Template inheritance (`base.html`), `{% block %}`, `{% include 'projects/includes/project_card.html' %}`, `{% for %}...{% empty %}`, built-in & custom filters (`deadline_badge`, `days_until`) | `templates/base.html`, `templates/projects/*.html`, `templates/accounts/*.html`, `projects/templatetags/project_extras.py` |
| **Unit IV: Forms, Validation & Security** | `ModelForm`, `UserCreationForm`, `{% csrf_token %}`, custom `clean_<field>()` validators (future deadline, team size 2–10, GitHub prefix, unique email), PRG pattern | `accounts/forms.py`, `projects/forms.py` |
| **Unit V: Models, ORM & Admin** | `OneToOneField`, `ForeignKey`, `ManyToManyField`, `UniqueConstraint`, signals, `Q` & `F` objects, `values()`, `annotate(Count(...))`, `select_related`, `prefetch_related`, `transaction.atomic()`, custom Admin permissions & bulk actions | `accounts/models.py`, `projects/models.py`, `accounts/signals.py`, `accounts/admin.py`, `projects/admin.py` |
| **Unit VI: Sessions, Cookies, Testing & Debugging** | Session-backed "Recently Viewed Projects" (last 5), Cookie-backed Light/Dark theme switcher, custom 403/404 handlers, 48 `TestCase` unit tests, Debug Toolbar notes | `projects/views.py`, `accounts/views.py`, `accounts/tests.py`, `projects/tests.py`, `teamup/settings.py` |
