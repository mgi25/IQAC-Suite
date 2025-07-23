# core/templatetags/dict_filters.py
from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    if dictionary and key:
        return dictionary.get(key)
    return None
