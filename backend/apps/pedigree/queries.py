"""
Выборки, которые неудобно выражать через ORM.

Родословная — граф, и предки достаются рекурсивным CTE Postgres
(см. «Модель данных» в CLAUDE.md). На 50 000 собак этого достаточно,
closure-таблица не нужна.
"""

from django.db import connection

# Позиции в дереве нумеруются как в двоичной куче: корень — 1,
# отец узла p — 2p, мать — 2p+1. Тогда поколение g занимает позиции
# от 2^g до 2^(g+1)-1, и по номеру позиции всегда понятно, где узел
# стоит и кем приходится корню.
ANCESTORS_SQL = """
WITH RECURSIVE ancestors AS (
    SELECT
        d.id,
        d.sire_id,
        d.dam_id,
        1::bigint      AS position,
        0              AS generation,
        ARRAY[d.id]    AS path
    FROM pedigree_dog d
    WHERE d.id = %(root_id)s

    UNION ALL

    SELECT
        parent.id,
        parent.sire_id,
        parent.dam_id,
        a.position * 2 + branch.side,
        a.generation + 1,
        a.path || parent.id
    FROM ancestors a
    -- Родителей разворачиваем в две строки: 0 — отцовская ветвь,
    -- 1 — материнская. «side», а не «offset»: последнее в Postgres
    -- зарезервировано. NULL-родители отсеются внутренним соединением.
    CROSS JOIN LATERAL (
        VALUES (a.sire_id, 0), (a.dam_id, 1)
    ) AS branch(parent_id, side)
    JOIN pedigree_dog parent ON parent.id = branch.parent_id
    WHERE a.generation < %(generations)s
      -- Защита от циклов. В данных из легаси собака вполне может
      -- оказаться собственным предком: транслитерация, дубли, ошибки
      -- ввода. Без этой строки запрос уходит в бесконечность.
      AND NOT parent.id = ANY(a.path)
)
SELECT id, position, generation FROM ancestors ORDER BY position;
"""


def ancestor_positions(root_id: int, generations: int) -> list[tuple[int, int, int]]:
    """
    Возвращает [(dog_id, position, generation)] для корня и его предков.

    `generations` — сколько поколений предков, не считая самой собаки:
    4 означает 4 ряда предков, всего до 31 узла.
    """
    with connection.cursor() as cursor:
        cursor.execute(ANCESTORS_SQL, {"root_id": root_id, "generations": generations})
        return cursor.fetchall()


def build_pedigree(root, generations: int) -> dict:
    """
    Собирает родословную для показа: узлы с раскладкой по сетке,
    отметки повторяющихся предков и полнота.

    Возвращает структуру, пригодную и шаблону, и JSON — чтобы серверная
    разметка и остров не разошлись.

    Раскладка считается здесь, а не в CSS: поколение g занимает столбец
    g+1, а по высоте — 2^(G-g) строк, где G — глубина. Так классический
    «гребень» родословной получается обычной сеткой, без вложенных таблиц.
    """
    from collections import Counter

    from .models import Dog

    rows = ancestor_positions(root.pk, generations)
    by_position = {position: dog_id for dog_id, position, _ in rows}

    dogs = {
        dog.pk: dog
        for dog in Dog.objects.filter(pk__in=by_position.values())
        .select_related("color")
        .prefetch_related("dog_titles__title", "health_tests__disease")
    }

    # Сколько раз каждый предок встречается в дереве. Корень не в счёт:
    # он там ровно один и подсвечивать его незачем.
    counts = Counter(dog_id for _, dog_id in by_position.items() if dog_id != root.pk)

    total_rows = 2 ** generations
    nodes = []

    for generation in range(generations + 1):
        span = 2 ** (generations - generation)
        for index in range(2 ** generation):
            position = 2 ** generation + index
            dog = dogs.get(by_position.get(position))
            nodes.append({
                "position": position,
                "generation": generation,
                "col": generation + 1,
                "row_start": index * span + 1,
                "row_span": span,
                # Отцовская ветвь идёт вверх, материнская вниз — это видно
                # по младшему биту позиции.
                "is_dam_line": bool(position % 2) and position > 1,
                **(_node_payload(dog, counts) if dog else {"dog": None}),
            })

    known = len(by_position) - 1                 # без самой собаки
    possible = 2 ** (generations + 1) - 2        # все места предков

    return {
        "root": {"name": root.name, "slug": root.slug, "url": root.get_absolute_url()},
        "generations": generations,
        "total_rows": total_rows,
        "nodes": nodes,
        "known": known,
        "possible": possible,
        "completeness": round(100 * known / possible, 1) if possible else 0.0,
        # Повторы нужны и легенде, и подсветке при наведении.
        "repeats": {str(k): v for k, v in counts.items() if v > 1},
    }


def _node_payload(dog, counts: dict) -> dict:
    """Данные одного узла дерева."""
    repeat = counts.get(dog.pk, 1)

    # Шкала подсветки рассчитана на 2, 3 и 4 повтора. Всё, что чаще,
    # схлопываем в старшую ступень: собака, встречающаяся семь раз,
    # и так уже кричит о себе.
    level = None
    if repeat > 1:
        level = min(repeat, 4)

    # Сводка по здоровью одним значением — худший известный результат.
    # У конкурента здоровья нет вовсе, а заводчику важно видеть проблему
    # прямо в дереве, а не открывая каждого предка по очереди.
    results = {test.result for test in dog.health_tests.all()}
    if "affected" in results:
        health = "affected"
    elif "carrier" in results:
        health = "carrier"
    elif "clear" in results:
        health = "clear"
    else:
        health = None

    return {
        "dog": {
            "id": dog.pk,
            "name": dog.name,
            # slug нужен острову: по нему он перестраивает дерево
            # от выбранного предка, не уходя со страницы.
            "slug": dog.slug,
            "url": dog.get_absolute_url(),
            "sex": dog.sex,
            "color": dog.color.name if dog.color else "",
            "born": dog.date_born.year if dog.date_born else None,
            "titles": [t.title.code for t in dog.dog_titles.all()][:6],
            "health": health,
            "repeat": repeat,
            "repeat_level": level,
        },
    }
