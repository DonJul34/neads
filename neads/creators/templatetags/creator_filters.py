from django import template

register = template.Library()

@register.filter
def mul(value, arg):
    """Multiplier filter."""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0 