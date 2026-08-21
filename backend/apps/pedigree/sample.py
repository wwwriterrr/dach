"""
Образец данных для вёрстки карточки собаки.

ВРЕМЕННЫЙ МОДУЛЬ. Существует, чтобы разложить интерфейс, пока схема
не согласована. Удаляется вместе с `views.sample_dog`, как только
появятся настоящие модели: шаблон читает атрибуты по тем же именам,
поэтому подмена сводится к замене источника в контексте.

Данные намеренно «неудобные» — то, что реально придёт из Drupal:
неизвестный родитель, пустые поля, собака с датой смерти, носитель
по одному заболеванию и поражённый по другому.
"""

from datetime import date

SAMPLE_DOG = {
    "nid": 314001,
    "name": "Fabeltier Vladimir Vladimirovich",
    "sex": "male",
    "titles": ["World Winner", "European Winner", "Russian Champion"],
    # Разновидность = размер + тип шерсти. Проект однопородный,
    # поэтому пишем без слова «такса» там, где оно и так очевидно.
    "size": "кроличья",
    "coat": "гладкошёрстная",
    "date_born": date(2013, 4, 26),
    "date_death": date(2026, 5, 30),
    "color": "шоколадно-подпалый",
    # Регистраций может быть несколько — разные организации разных стран.
    "registrations": [
        {"organisation": "РКФ", "number": "RKF 3421890"},
        {"organisation": "FCI", "number": "FCI 148/2013"},
    ],
    "microchip": "643094100123456",
    "tattoo": "",
    "weight_kg": "4.1",
    "chest_cm": "32",
    "photos_count": 6,
    "has_video": True,
    # Происхождение записи: чем она подтверждена и кем.
    "provenance": {
        "status": "verified",
        "label": "Проверено",
        "detail": "Скан родословной РКФ, сверено 12.03.2024",
    },
    "sire": {"nid": 298114, "name": "Crisscross Downtown Brown KtS"},
    "dam": {"nid": 30177, "name": "Magik Rainbow Je t'aime Courage"},
    "breeder": "Виктория Иванова и Василий Иванов (Magik Rainbow, Россия)",
    "owner": "",
    # COI считается ночной задачей Celery и берётся готовым.
    "coi": {
        "value": "6.42",
        "generations": 10,
        "known_ancestors": "87.2",
        "calculated_at": date(2026, 8, 20),
    },
    # Здоровье — главный дифференциатор. Порядок: сначала то,
    # что влияет на подбор пары, потом остальное.
    "health": [
        {
            "title": "IVDD / CDDY (FGF4-12)",
            "status": "affected",
            "status_label": "Поражён",
            "genotype": "CDDY/CDDY",
            "lab": "Laboklin",
            "tested_on": date(2014, 2, 18),
        },
        {
            "title": "Болезнь Лафоры (NHLRC1)",
            "status": "carrier",
            "status_label": "Носитель",
            "genotype": "N/L",
            "lab": "Laboklin",
            "tested_on": date(2014, 2, 18),
        },
        {
            "title": "cord1-PRA (RPGRIP1)",
            "status": "clear",
            "status_label": "Чист",
            "genotype": "N/N",
            "lab": "Laboklin",
            "tested_on": date(2014, 2, 18),
        },
        {
            "title": "Локус M (дапл)",
            "status": "clear",
            "status_label": "Не дапл",
            "genotype": "m/m",
            "lab": "Laboklin",
            "tested_on": date(2014, 2, 18),
        },
    ],
    "field_trials": {"total": 3},
    "siblings": {"total": 22, "males": 11, "females": 11},
    "offspring": {"total": 220},
}
