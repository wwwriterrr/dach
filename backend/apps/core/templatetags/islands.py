"""
Тег для встраивания React-острова в Django-шаблон.

    {% load islands %}
    {% island "demo-search" placeholder="Кличка или номер" limit=20 %}

Рендерит контейнер, который на клиенте находит frontend/src/main.tsx
и монтирует в него компонент из реестра островов (frontend/src/islands/registry.ts).
Имя острова должно совпадать с ключом в реестре.
"""

import json

from django import template
from django.utils.html import format_html

register = template.Library()


@register.simple_tag
def island(name: str, **props) -> str:
    # format_html экранирует и имя, и JSON — значения безопасны в атрибуте
    payload = json.dumps(props, ensure_ascii=False, default=str)
    return format_html(
        '<div data-island="{}" data-props="{}"></div>',
        name,
        payload,
    )
