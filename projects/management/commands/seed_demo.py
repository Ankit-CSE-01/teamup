from datetime import timedelta
from django.contrib.auth.models import Group, Permission, User
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.text import slugify

from accounts.models import Profile, Skill
from projects.models import JoinRequest, Project


class Command(BaseCommand):
    help = "Seeds 15 skills, Faculty/Students groups, 8 demo users, 12 projects, and sample join requests."

    def handle(self, *args, **options):
        self.stdout.write("Starting TeamUp demo seed...")

        # 1. Create Groups & Permissions (Unit V / Admin requirement)
        faculty_group, _ = Group.objects.get_or_create(name="Faculty")
        student_group, _ = Group.objects.get_or_create(name="Students")

        # Give Faculty view permissions on Project, JoinRequest, Profile, Skill, and User
        for model_cls in (Project, JoinRequest, Profile, Skill, User):
            ct = ContentType.objects.get_for_model(model_cls)
            view_perms = Permission.objects.filter(
                content_type=ct, codename__startswith="view_"
            )
            faculty_group.permissions.add(*view_perms)

        # Give Students add/change/view permissions on Project and JoinRequest
        for model_cls in (Project, JoinRequest):
            ct = ContentType.objects.get_for_model(model_cls)
            student_perms = Permission.objects.filter(
                content_type=ct,
                codename__in=[
                    f"add_{model_cls._meta.model_name}",
                    f"change_{model_cls._meta.model_name}",
                    f"view_{model_cls._meta.model_name}",
                ],
            )
            student_group.permissions.add(*student_perms)

        self.stdout.write(
            self.style.SUCCESS("Configured 'Faculty' and 'Students' permission groups.")
        )

        # 2. Seed 15 Technical Skills
        skill_names = [
            "Python",
            "Django",
            "React",
            "Machine Learning",
            "Flutter",
            "DSA",
            "Node.js",
            "PostgreSQL",
            "Docker",
            "AWS",
            "TypeScript",
            "PyTorch",
            "UI/UX Figma",
            "Cybersecurity",
            "Solidity",
        ]
        skills_map = {}
        for name in skill_names:
            slug = slugify(name)
            skill, _ = Skill.objects.get_or_create(name=name, defaults={"slug": slug})
            skills_map[name] = skill

        self.stdout.write(self.style.SUCCESS(f"Seeded {len(skills_map)} skills."))

        # 3. Seed 8 Demo Users (7 Students + 1 Faculty member)
        demo_users_data = [
            {
                "username": "aarav_sharma",
                "email": "aarav@cse.univ.edu",
                "full_name": "Aarav Sharma",
                "year": 3,
                "branch": "CSE",
                "bio": "Full-stack developer passionate about Django, React, and Smart India Hackathon.",
                "github": "https://github.com/aaravsharma",
                "skills": ["Python", "Django", "React", "PostgreSQL", "Docker"],
                "is_faculty": False,
            },
            {
                "username": "priya_nair",
                "email": "priya@cse.univ.edu",
                "full_name": "Priya Nair",
                "year": 4,
                "branch": "CSE (AI & ML)",
                "bio": "Working on computer vision and NLP research papers. Looking for publication co-authors.",
                "github": "https://github.com/priyanair-ai",
                "skills": ["Python", "Machine Learning", "PyTorch", "DSA"],
                "is_faculty": False,
            },
            {
                "username": "rohan_verma",
                "email": "rohan@cse.univ.edu",
                "full_name": "Rohan Verma",
                "year": 2,
                "branch": "CSE",
                "bio": "Mobile app builder using Flutter and Firebase. Winning campus hackathons one weekend at a time.",
                "github": "https://github.com/rohanverma-dev",
                "skills": ["Flutter", "UI/UX Figma", "Node.js", "TypeScript"],
                "is_faculty": False,
            },
            {
                "username": "sneha_reddy",
                "email": "sneha@cse.univ.edu",
                "full_name": "Sneha Reddy",
                "year": 3,
                "branch": "CSE",
                "bio": "Cloud architecture & DevOps enthusiast. Love automating deployments and securing APIs.",
                "github": "https://github.com/snehareddy",
                "skills": ["Docker", "AWS", "Python", "Cybersecurity", "PostgreSQL"],
                "is_faculty": False,
            },
            {
                "username": "kabir_khan",
                "email": "kabir@cse.univ.edu",
                "full_name": "Kabir Khan",
                "year": 2,
                "branch": "IT",
                "bio": "Competitive programmer (5-star) and Web3 smart contract developer.",
                "github": "https://github.com/kabirkhan-cp",
                "skills": ["DSA", "Solidity", "React", "TypeScript"],
                "is_faculty": False,
            },
            {
                "username": "anya_gupta",
                "email": "anya@cse.univ.edu",
                "full_name": "Anya Gupta",
                "year": 1,
                "branch": "CSE",
                "bio": "First-year designer and frontend coder eager to join mini-projects and learn Django.",
                "github": "https://github.com/anyagupta",
                "skills": ["UI/UX Figma", "React", "Python"],
                "is_faculty": False,
            },
            {
                "username": "vikram_singh",
                "email": "vikram@cse.univ.edu",
                "full_name": "Vikram Singh",
                "year": 4,
                "branch": "CSE",
                "bio": "Building a campus EdTech SaaS startup. Looking for technical co-founders.",
                "github": "https://github.com/vikramsingh",
                "skills": ["Django", "React", "AWS", "PostgreSQL", "Node.js"],
                "is_faculty": False,
            },
            {
                "username": "prof_mehta",
                "email": "mehta.faculty@cse.univ.edu",
                "full_name": "Dr. Rajesh Mehta (Faculty Coordinator)",
                "year": 4,
                "branch": "CSE Faculty",
                "bio": "Faculty Project Coordinator overseeing Capstone & Research collaborations.",
                "github": "https://github.com/profmehta-lab",
                "skills": ["Python", "Machine Learning", "Cybersecurity", "DSA"],
                "is_faculty": True,
            },
        ]

        users_map = {}
        for udata in demo_users_data:
            user, created = User.objects.get_or_create(
                username=udata["username"],
                defaults={
                    "email": udata["email"],
                    "is_staff": udata["is_faculty"],
                },
            )
            if created:
                user.set_password("teamup123")
                user.save()

            if udata["is_faculty"]:
                user.groups.add(faculty_group)

            profile = user.profile
            profile.full_name = udata["full_name"]
            profile.year_of_study = udata["year"]
            profile.branch = udata["branch"]
            profile.bio = udata["bio"]
            profile.github_url = udata["github"]
            profile.save()
            profile.skills.set([skills_map[s] for s in udata["skills"]])

            users_map[udata["username"]] = user

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {len(users_map)} demo users (password: teamup123)."
            )
        )

        # 4. Seed 12 Projects across all 5 categories
        today = timezone.localdate()
        projects_data = [
            {
                "title": "Smart India Hackathon: AI Traffic Signal Optimizer",
                "description": "Building a real-time emergency corridor and adaptive traffic light system using YOLO object detection and a Django dashboard for municipal control rooms.",
                "category": Project.CATEGORY_HACKATHON,
                "owner": "aarav_sharma",
                "skills": ["Python", "Django", "Machine Learning", "React"],
                "team_size": 6,
                "days_ahead": 25,
                "status": Project.STATUS_OPEN,
            },
            {
                "title": "MedChain: Decentralized Patient Health Records",
                "description": "A zero-knowledge proof and Solidity smart contract platform allowing patients to grant temporary diagnostic access to hospitals.",
                "category": Project.CATEGORY_HACKATHON,
                "owner": "kabir_khan",
                "skills": ["Solidity", "React", "TypeScript", "Node.js"],
                "team_size": 4,
                "days_ahead": 18,
                "status": Project.STATUS_OPEN,
            },
            {
                "title": "INT253 Course Mini Project: Hostel Mess Feedback Portal",
                "description": "A web portal for students to rate daily meals, view nutritional breakdowns, and help the mess committee reduce food wastage.",
                "category": Project.CATEGORY_MINI,
                "owner": "anya_gupta",
                "skills": ["Python", "Django", "UI/UX Figma", "PostgreSQL"],
                "team_size": 3,
                "days_ahead": 30,
                "status": Project.STATUS_OPEN,
            },
            {
                "title": "Algorithm Visualizer & DSA Practice Arena",
                "description": "Interactive step-by-step visualization tool for graph algorithms, dynamic programming tables, and segment trees.",
                "category": Project.CATEGORY_MINI,
                "owner": "kabir_khan",
                "skills": ["DSA", "React", "TypeScript"],
                "team_size": 3,
                "days_ahead": 40,
                "status": Project.STATUS_OPEN,
            },
            {
                "title": "Autonomous Drone Crop Disease Detection (Final Year Capstone)",
                "description": "Final year major project combining multispectral leaf imaging with PyTorch vision transformers and a Flutter field inspection app.",
                "category": Project.CATEGORY_MAJOR,
                "owner": "priya_nair",
                "skills": ["Python", "Machine Learning", "PyTorch", "Flutter"],
                "team_size": 4,
                "days_ahead": 60,
                "status": Project.STATUS_OPEN,
            },
            {
                "title": "Cloud-Native Zero-Trust Campus Network Monitor",
                "description": "Capstone project detecting anomalous packet flows and unauthorized IoT devices across university Wi-Fi subnets.",
                "category": Project.CATEGORY_MAJOR,
                "owner": "sneha_reddy",
                "skills": ["Cybersecurity", "Docker", "AWS", "Python"],
                "team_size": 4,
                "days_ahead": 55,
                "status": Project.STATUS_OPEN,
            },
            {
                "title": "Low-Resource Indic Language LLM Fine-Tuning",
                "description": "Undergraduate research paper targeting IEEE submission on parameter-efficient LoRA fine-tuning for regional educational datasets.",
                "category": Project.CATEGORY_RESEARCH,
                "owner": "priya_nair",
                "skills": ["Python", "Machine Learning", "PyTorch"],
                "team_size": 3,
                "days_ahead": 75,
                "status": Project.STATUS_OPEN,
            },
            {
                "title": "Adversarial Robustness in Intrusion Detection Systems",
                "description": "Faculty-guided research investigating evasion attacks on deep learning firewalls and proposing defensive distillation.",
                "category": Project.CATEGORY_RESEARCH,
                "owner": "prof_mehta",
                "skills": ["Cybersecurity", "Machine Learning", "Python", "DSA"],
                "team_size": 3,
                "days_ahead": 90,
                "status": Project.STATUS_OPEN,
            },
            {
                "title": "CampusCart: Hyperlocal Peer-to-Peer Textbook & Lab Kit Rental",
                "description": "Student startup incubated at the university E-Cell. Mobile app for renting drafters, IoT sensors, and semester books within campus hostels.",
                "category": Project.CATEGORY_STARTUP,
                "owner": "rohan_verma",
                "skills": ["Flutter", "Node.js", "PostgreSQL", "UI/UX Figma"],
                "team_size": 5,
                "days_ahead": 45,
                "status": Project.STATUS_OPEN,
            },
            {
                "title": "PrepPulse: AI Mock Interviewer for Campus Placements",
                "description": "SaaS startup helping 3rd and 4th year students practice technical DSA and system design interviews with automated rubric scoring.",
                "category": Project.CATEGORY_STARTUP,
                "owner": "vikram_singh",
                "skills": ["Django", "React", "AWS", "PostgreSQL", "Machine Learning"],
                "team_size": 5,
                "days_ahead": 50,
                "status": Project.STATUS_OPEN,
            },
            {
                "title": "UniShuttle: Real-Time Campus Bus GPS Tracker",
                "description": "Cross-platform mobile app showing live shuttle ETA between academic blocks and hostels.",
                "category": Project.CATEGORY_MINI,
                "owner": "rohan_verma",
                "skills": ["Flutter", "Django", "Docker"],
                "team_size": 4,
                "days_ahead": 20,
                "status": Project.STATUS_OPEN,
            },
            {
                "title": "FinHack 2026: Automated UPI Expense Categorizer (Team Full)",
                "description": "Hackathon project that won 2nd place in regional qualifiers. Team roster is now locked.",
                "category": Project.CATEGORY_HACKATHON,
                "owner": "aarav_sharma",
                "skills": ["Python", "Django", "React"],
                "team_size": 4,
                "days_ahead": 10,
                "status": Project.STATUS_CLOSED,
            },
        ]

        created_projects = []
        for pdata in projects_data:
            proj, _ = Project.objects.get_or_create(
                title=pdata["title"],
                defaults={
                    "owner": users_map[pdata["owner"]],
                    "description": pdata["description"],
                    "category": pdata["category"],
                    "team_size_needed": pdata["team_size"],
                    "deadline": today + timedelta(days=pdata["days_ahead"]),
                    "status": pdata["status"],
                },
            )
            proj.skills_needed.set([skills_map[s] for s in pdata["skills"]])
            created_projects.append(proj)

        self.stdout.write(
            self.style.SUCCESS(f"Seeded {len(created_projects)} projects.")
        )

        # 5. Seed Sample JoinRequests
        join_requests_data = [
            (
                created_projects[0],
                users_map["priya_nair"],
                "I have trained YOLOv8 models in PyTorch for vehicle detection and can lead the ML pipeline.",
                JoinRequest.STATUS_ACCEPTED,
            ),
            (
                created_projects[0],
                users_map["sneha_reddy"],
                "I can containerize the Django + inference server using Docker and deploy it on AWS.",
                JoinRequest.STATUS_PENDING,
            ),
            (
                created_projects[0],
                users_map["anya_gupta"],
                "I can design the municipal dashboard UI in Figma and build the React components!",
                JoinRequest.STATUS_PENDING,
            ),
            (
                created_projects[2],
                users_map["aarav_sharma"],
                "Happy to mentor and build the Django backend models and PostgreSQL schema with you.",
                JoinRequest.STATUS_ACCEPTED,
            ),
            (
                created_projects[4],
                users_map["rohan_verma"],
                "I can build the offline-first Flutter mobile app for farmers and field testing.",
                JoinRequest.STATUS_PENDING,
            ),
            (
                created_projects[9],
                users_map["aarav_sharma"],
                "Experienced with Django REST & React; would love to co-build the interview rubric engine.",
                JoinRequest.STATUS_PENDING,
            ),
            (
                created_projects[8],
                users_map["anya_gupta"],
                "I designed a prototype for a hostel rental app last semester—can share my Figma link!",
                JoinRequest.STATUS_REJECTED,
            ),
        ]

        for proj, applicant, msg, status in join_requests_data:
            JoinRequest.objects.get_or_create(
                project=proj,
                applicant=applicant,
                defaults={"message": msg, "status": status},
            )

        self.stdout.write(
            self.style.SUCCESS(
                "Successfully seeded join requests! Demo login: 'aarav_sharma' / 'teamup123'"
            )
        )
