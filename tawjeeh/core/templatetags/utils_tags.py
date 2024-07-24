from django import template

register = template.Library()


@register.filter
def listify(iterable):
    return list(iterable)
