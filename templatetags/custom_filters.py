from django import template

register = template.Library()

@register.filter
def range_num(num):
    """
    Фильтр для создания диапазона чисел от 0 до num-1.
    Пример использования: {% for i in 5|range_num %}
    """
    return range(int(num))

@register.filter
def mul(value, arg):
    """
    Фильтр для умножения value на arg.
    Пример использования: {{ value|mul:2 }}
    """
    return value * arg

@register.filter
def div(value, arg):
    """
    Фильтр для деления value на arg.
    Пример использования: {{ value|div:2 }}
    """
    return value / arg if arg != 0 else 0

@register.filter
def add(value, arg):
    """
    Фильтр для сложения value и arg.
    Пример использования: {{ value|add:2 }}
    """
    return value + arg

@register.filter
def sub(value, arg):
    """
    Фильтр для вычитания arg из value.
    Пример использования: {{ value|sub:2 }}
    """
    return value - arg