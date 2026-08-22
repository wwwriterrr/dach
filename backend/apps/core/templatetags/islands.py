"""
Тег для встраивания React-острова в Django-шаблон.

    {% load islands %}
    {% island "dog-search" props=island_props %}
      <form method="get">…</form>   {# серверный вариант того же самого #}
    {% endisland %}

Внутрь тега кладётсяработающая серверная разметка. Она попадает
в HTML и остаётся там для поисковых роботов и посетителей без JS.
На клиенте main.tsx находит контейнер, берёт компонент из реестра
(frontend/src/registry.ts) и подменяет содержимое интерактивной версией.

Тег намеренно сделан блочным даже там, где запасного варианта нет:
пустой {% island "x" %}{% endisland %} — это явно принятое решение,
что без JS раздел не работает, а не случайно забытый запасной путь.
Для справочника, живущего поисковым трафиком, разница существенная.
"""

import json

from django import template
from django.utils.html import format_html
from django.utils.safestring import mark_safe

register = template.Library()


@register.simple_block_tag
def island(content, name: str, props: dict | None = None, **kwargs) -> str:
    # props передаются либо словарём, либо отдельными аргументами
    payload = {**(props or {}), **kwargs}
    return format_html(
        '<div data-island="{}" data-props="{}">{}</div>',
        name,
        json.dumps(payload, ensure_ascii=False, default=str),
        mark_safe(content),
    )
