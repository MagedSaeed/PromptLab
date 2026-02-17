from django import template

register = template.Library()


@register.filter
def listify(iterable):
    return list(iterable)


@register.filter
def get_range(value):
    return range(value)


@register.filter
def div(value, arg):
    try:
        return int(value) / int(arg)
    except (ValueError, ZeroDivisionError):
        return None


@register.filter
def mul(value, arg):
    try:
        return int(value) * int(arg)
    except ValueError:
        return None
