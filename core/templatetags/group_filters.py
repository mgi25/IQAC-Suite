from django import template

# Single shared Library instance for all filters in this module
register = template.Library()


@register.filter
def get_item(d, key):
    """Safely get a key from a dict-like in templates."""
    try:
        return d.get(key)
    except Exception:
        return None


@register.filter
def has_group(user, group_name):
    """Check if a user belongs to a given Django auth group by name."""
    if user and group_name:
        return user.groups.filter(name=group_name).exists()
    return False

