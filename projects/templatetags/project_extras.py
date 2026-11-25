from datetime import date, datetime
from django import template
from django.utils import timezone
from django.utils.html import format_html

register = template.Library()


@register.filter(name="days_until")
def days_until(deadline):
    """
    Return the integer number of days from today until `deadline`.
    Returns None if deadline is invalid.
    Usage: {{ project.deadline|days_until }}
    """
    if not deadline:
        return None
    if isinstance(deadline, datetime):
        deadline = deadline.date()
    if not isinstance(deadline, date):
        return None

    today = timezone.localdate()
    return (deadline - today).days


@register.filter(name="deadline_badge")
def deadline_badge(deadline, status="Open"):
    """
    Render a color-coded HTML badge showing days remaining or urgency state.
    - Closed projects -> neutral 'Closed' badge
    - Past deadline (< 0 days) -> red 'Deadline Passed' badge
    - Due today (0 days) -> red 'Closing Today!' badge
    - Due in 1-5 days -> amber 'Closing Soon (Xd left)' badge
    - Due in > 5 days -> green 'Xd left' badge

    Usage:
        {% load project_extras %}
        {{ project.deadline|deadline_badge:project.status }}
    """
    if status == "Closed":
        return format_html(
            '<span class="badge {}" title="{}">{}</span>',
            "deadline-closed",
            "Applications are closed",
            "Closed",
        )

    delta_days = days_until(deadline)
    if delta_days is None:
        return ""

    if delta_days < 0:
        overdue = abs(delta_days)
        day_word = "day" if overdue == 1 else "days"
        return format_html(
            '<span class="badge deadline-urgent" title="Ended {} {} ago">Deadline Passed</span>',
            overdue,
            day_word,
        )

    if delta_days == 0:
        return format_html(
            '<span class="badge {}" title="{}">{}</span>',
            "deadline-urgent",
            "Final day to apply",
            "⏰ Closing Today!",
        )

    if delta_days <= 5:
        day_word = "day" if delta_days == 1 else "days"
        return format_html(
            '<span class="badge deadline-soon" title="Hurry! Only {} {} remaining">🔥 Closing Soon • {}d left</span>',
            delta_days,
            day_word,
            delta_days,
        )

    return format_html(
        '<span class="badge deadline-normal" title="Application deadline countdown">📅 {}d left</span>',
        delta_days,
    )
