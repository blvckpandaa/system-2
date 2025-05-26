from django import template

register = template.Library()

@register.filter
def mod(value, arg):
    """
    Фильтр для получения остатка от деления value на arg.
    Пример использования: {{ value|mod:2 }}
    """
    try:
        return int(value) % int(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def mul(value, arg):
    """
    Фильтр для умножения value на arg.
    Пример использования: {{ value|mul:2 }}
    """
    try:
        return int(value) * int(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def range_num(num):
    """
    Фильтр для создания диапазона чисел от 0 до num-1.
    Пример использования: {% for i in 5|range_num %}...{% endfor %}
    """
    try:
        num = int(num)
        return range(num)
    except (ValueError, TypeError):
        return range(0)

@register.filter
def add(value, arg):
    """
    Фильтр для сложения value и arg.
    Пример использования: {{ value|add:2 }}
    """
    try:
        return int(value) + int(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def sub(value, arg):
    """
    Фильтр для вычитания arg из value.
    Пример использования: {{ value|sub:2 }}
    """
    try:
        return int(value) - int(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def div(value, arg):
    """
    Фильтр для деления value на arg.
    Пример использования: {{ value|div:2 }}
    """
    try:
        arg = int(arg)
        if arg == 0:
            return 0
        return int(value) / arg
    except (ValueError, TypeError):
        return 0 