from django import template

register = template.Library()

@register.filter
def mod(value, arg):
    """Возвращает остаток от деления value на arg"""
    try:
        return int(value) % int(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def mul(value, arg):
    """Умножает value на arg"""
    try:
        return int(value) * int(arg)
    except (ValueError, TypeError):
        return 0 