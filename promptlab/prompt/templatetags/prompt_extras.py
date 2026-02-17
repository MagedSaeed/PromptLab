import re

from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter(name="highlight")
def highlight(text, search_term):
    """
    Highlights all occurrences of the search term in the text.
    Usage: {{ value|highlight:search_term }}
    """
    if not text or not search_term:
        return text

    pattern = re.compile(f"({re.escape(search_term)})", re.IGNORECASE)
    highlighted = pattern.sub(r'<span class="highlight">\1</span>', str(text))
    return mark_safe(highlighted)


@register.filter(name="contains")
def contains(value, arg):
    """
    Check if a string contains a substring (case-insensitive)
    Usage: {{ value|contains:substring }}
    """
    if not value or not arg:
        return False
    return arg.lower() in value.lower()
