"""
Склонение существительных при числительных.

Встроенный `pluralize` рассчитан на английский — две формы. В русском
их три, и правило зависит от последних двух цифр:

    1 кобель, 2 кобеля, 5 кобелей, 11 кобелей, 21 кобель

    {{ n }} {{ n|plural:"кобель,кобеля,кобелей" }}
"""

from django import template

register = template.Library()


@register.filter
def plural(value, forms: str) -> str:
    """`forms` — три формы через запятую: для 1, для 2-4, для 5-20."""
    try:
        number = abs(int(value))
    except (TypeError, ValueError):
        return ""

    one, few, many = (f.strip() for f in forms.split(","))

    if number % 100 in range(11, 15):
        return many
    if number % 10 == 1:
        return one
    if number % 10 in (2, 3, 4):
        return few
    return many
