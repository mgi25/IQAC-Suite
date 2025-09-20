# core/templatetags/dict_filters.py
from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    if dictionary and key:
        return dictionary.get(key)
    return None


@register.filter
def get_list(querydict, key):
    """Return a list of values from a QueryDict-like object."""
    if querydict and key:
        getlist = getattr(querydict, "getlist", None)
        if callable(getlist):
            return getlist(key)
    return []
