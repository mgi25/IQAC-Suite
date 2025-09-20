# core/templatetags/group_filters.py
from django import template

register = template.Library()


@register.filter
def has_group(user, group_name):
    if user and group_name:
        return user.groups.filter(name=group_name).exists()
    return False
