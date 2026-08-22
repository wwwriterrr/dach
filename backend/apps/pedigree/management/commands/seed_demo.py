"""
Демонстрационные данные для разработки интерфейса.

Не фикстуры для тестов и тем более не то, что поедет в прод: задача —
наполнить стенд, пока нет дампа, и заодно проверить, держит ли схема
грязь. Поэтому данные намеренно неровные: собаки без родителей,
с одним известным родителем, без даты рождения, с кличкой кириллицей,
дубли и мусорная запись вроде тех, что нашлись в легаси.

    python manage.py seed_demo --flush

Родословная строится поколениями сверху вниз, поэтому циклов не будет
по построению. Часть кобелей назначается «популярными производителями»
и используется многократно — так в родословных появляются повторяющиеся
предки, ради которых существует шкала подсветки.
"""

import random
from datetime import date, timedelta
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from apps.pedigree.models import (
    Coat, Coi, Color, Country, Disease, Dog, DogTitle, HealthResult, HealthTest,
    Kennel, Litter, Person, Provenance, Registration, Sex, Size, Title, TitleKind,
)

COUNTRIES = [
    ("RU", "Россия"), ("BY", "Беларусь"), ("UA", "Украина"), ("CZ", "Чехия"),
    ("DE", "Германия"), ("PL", "Польша"), ("FI", "Финляндия"), ("US", "США"),
    ("GB", "Великобритания"), ("FR", "Франция"),
]

# Окрасы таксы. Дапл — локус M, помечаем отдельно: на нём держится
# половина смысла пробной вязки.
COLORS = [
    ("рыжий", False, False),
    ("кремовый", False, False),
    ("чёрно-подпалый", False, False),
    ("шоколадно-подпалый", False, False),
    ("кабаний", False, False),
    ("чёрно-подпалый дапл", True, False),
    ("шоколадный дапл", True, False),
    ("рыжий дапл", True, False),
    ("двойной дапл", True, True),
]

# Реальные для породы тесты. Лафора почти исключительно у жесткошёрстных
# кроличьих, cord1 — у гладких и длинных.
DISEASES = [
    ("ivdd-cddy", "IVDD / CDDY", "FGF4-12", []),
    ("lafora", "Болезнь Лафоры", "NHLRC1", [Coat.WIRE]),
    ("cord1-pra", "cord1-PRA", "RPGRIP1", [Coat.SMOOTH, Coat.LONG]),
    ("patella", "Вывих коленной чашечки", "", []),
    ("m-locus", "Локус M (дапл)", "PMEL", []),
]

PREFIXES = [
    "Fabeltier", "Magik Rainbow", "Crisscross", "Minidogland", "Kaladium-Vizavi",
    "Lisego Nosa", "Norden Liht", "Ygeia", "Grandgables", "Taksa-Klass",
    "SoKisable", "Dynadaux", "Star City", "Armidach", "Kinchville",
]
GIVEN_M = [
    "Vladimir", "Olimpus", "Timofey", "Disco", "Ordinar", "Harmony", "Kasper",
    "Boots", "Carpaccio", "Mumbo Jumbo", "Teddy Boy", "Light Rey", "Kornet",
]
GIVEN_F = [
    "Jacqueline", "Naomi", "Rihanna", "Leonsia", "Courage", "Idoliz", "Fifa",
    "Stunning", "Wee Wonder", "Girl", "Dakota", "Pampa", "Medovaya Radost",
]
HOME_NAMES = ["Гера", "Винни", "Тима", "Люся", "Барон", "Марта", "", "", ""]
LABS = ["Laboklin", "Zoogen", "Antagene", "Embark", ""]
ORGS = ["РКФ", "FCI", "AKC", "KC", "VDH"]


class Command(BaseCommand):
    help = "Наполняет базу демонстрационными данными для вёрстки"

    def add_arguments(self, parser):
        parser.add_argument("--dogs", type=int, default=400, help="сколько собак создать")
        parser.add_argument("--flush", action="store_true", help="сначала стереть текущие")
        parser.add_argument("--seed", type=int, default=20260822, help="зерно генератора")

    @transaction.atomic
    def handle(self, *args, **options):
        rnd = random.Random(options["seed"])

        if options["flush"]:
            self._flush()

        countries = self._countries()
        titles = self._titles()
        colors = self._colors()
        diseases = self._diseases()
        kennels = self._kennels(rnd, countries)
        people = self._people(rnd, kennels, countries)

        dogs = self._dogs(rnd, options["dogs"], colors, kennels, people)
        self._titles_for_dogs(rnd, dogs, titles)
        self._registrations(rnd, dogs)
        self._health(rnd, dogs, diseases)
        self._coi(rnd, dogs)
        self._dirt(rnd, colors)

        self.stdout.write(self.style.SUCCESS(
            f"готово: {Dog.objects.count()} собак, {Litter.objects.count()} помётов, "
            f"{HealthTest.objects.count()} тестов, {Person.objects.count()} человек, "
            f"{Kennel.objects.count()} питомников"
        ))

    # --- очистка ---------------------------------------------------------

    def _flush(self):
        for model in (Coi, HealthTest, Registration, DogTitle, Dog, Litter,
                      Person, Kennel, Disease, Color, Title, Country):
            model.objects.all().delete()
        self.stdout.write("прежние данные стёрты")

    # --- справочники -----------------------------------------------------

    def _countries(self):
        return [Country.objects.get_or_create(code=c, defaults={"name": n})[0]
                for c, n in COUNTRIES]

    def _titles(self):
        """Берём настоящий словарь легаси — 121 аббревиатура из аудита."""
        path = Path(__file__).resolve().parents[2] / "data" / "titles.txt"
        # Построчно, а не split(): часть титулов содержит пробел —
        # «WUT CH», «DTK JCH», — и split() разорвал бы их надвое.
        codes = ([c.strip() for c in path.read_text(encoding="utf-8").splitlines() if c.strip()]
                 if path.exists() else ["INTCH", "WW", "EUW", "RKFCH", "RUSCH", "RUSJCH"])
        out = []
        for code in codes:
            kind = TitleKind.FIELD if code.startswith("FT") else TitleKind.SHOW
            out.append(Title.objects.get_or_create(code=code, defaults={"kind": kind})[0])
        return out

    def _colors(self):
        return [Color.objects.get_or_create(
            name=n, defaults={"is_dapple": d, "is_double_dapple": dd})[0]
            for n, d, dd in COLORS]

    def _diseases(self):
        return [Disease.objects.get_or_create(
            code=c, defaults={"name": n, "gene": g, "relevant_coats": coats})[0]
            for c, n, g, coats in DISEASES]

    # --- люди и питомники ------------------------------------------------

    def _kennels(self, rnd, countries):
        out = []
        for i, name in enumerate(PREFIXES):
            out.append(Kennel.objects.create(
                name=name, slug=self._slug(name, "kennel", i),
                country=rnd.choice(countries),
                legacy_id=10_000 + i, provenance=Provenance.IMPORTED,
            ))
        return out

    def _people(self, rnd, kennels, countries):
        first = ["Виктория", "Василий", "Анна", "Дмитрий", "Ольга", "Сергей", "Марина"]
        last = ["Иванова", "Иванов", "Петрова", "Смирнов", "Ковалёва", "Новак"]
        out = []
        for i in range(40):
            name = f"{rnd.choice(first)} {rnd.choice(last)}"
            kennel = rnd.choice(kennels) if rnd.random() < 0.7 else None
            out.append(Person.objects.create(
                name=name, slug=self._slug(name, "person", i),
                kennel=kennel, country=rnd.choice(countries),
                # Так эта строка выглядит в легаси — одним куском.
                raw_name=f"{name} ( {kennel.name.upper() if kennel else ''} )".strip(),
                legacy_id=20_000 + i, provenance=Provenance.IMPORTED,
            ))
        return out

    # --- собаки ----------------------------------------------------------

    def _dogs(self, rnd, total, colors, kennels, people):
        """
        Строим поколениями сверху вниз: сначала основатели без родителей,
        затем каждое следующее поколение рождается помётами от пар
        предыдущего. Циклы невозможны по построению.

        Рождаем именно помётами, а не поштучно: если выбирать родителей
        независимо для каждого щенка, пары почти не повторяются и
        однопомётников не возникает — а это одна из основных связей
        в справочнике.
        """
        generations, per_gen = 6, max(8, total // 6)
        all_dogs, prev_males, prev_females = [], [], []
        counter = 0

        for gen in range(generations):
            males, females = [], []
            born_from = date(2005, 1, 1) + timedelta(days=gen * 900)
            made = 0

            while made < per_gen:
                sire = dam = litter = None
                if prev_males and prev_females:
                    # «Эффект популярного производителя»: треть кобелей
                    # предыдущего поколения даёт большинство потомства —
                    # отсюда повторяющиеся предки в родословных.
                    pool = prev_males[: max(1, len(prev_males) // 3)]
                    sire = rnd.choice(pool if rnd.random() < 0.75 else prev_males)
                    dam = rnd.choice(prev_females)

                litter_size = min(rnd.randint(2, 6), per_gen - made)
                litter_born = born_from + timedelta(days=rnd.randint(0, 800))

                if sire and dam:
                    litter = Litter.objects.create(
                        sire=sire, dam=dam, date_born=litter_born,
                        kennel=rnd.choice(kennels), letter=rnd.choice("ABCDEFGHIJK"),
                        provenance=Provenance.IMPORTED,
                    )

                for _ in range(litter_size):
                    sex = Sex.MALE if rnd.random() < 0.5 else Sex.FEMALE
                    name = f"{rnd.choice(PREFIXES)} {rnd.choice(GIVEN_M if sex == Sex.MALE else GIVEN_F)}"
                    dog = Dog.objects.create(
                        name=name, slug=self._slug(name, "dog", counter),
                        home_name=rnd.choice(HOME_NAMES),
                        sex=sex,
                        size=rnd.choice(list(Size.values)),
                        coat=rnd.choice(list(Coat.values)),
                        color=rnd.choice(colors) if rnd.random() < 0.85 else None,
                        color_raw=rnd.choice(["black&tan", "brown&tan",
                                              "Chocolate & Tan Dapple", "red"]),
                        # Часть щенков помёта остаётся без даты — в легаси
                        # дата рождения известна далеко не у всех.
                        date_born=litter_born if rnd.random() < 0.8 else None,
                        sire=sire, dam=dam, litter=litter, kennel=rnd.choice(kennels),
                        breeder=rnd.choice(people) if rnd.random() < 0.6 else None,
                        owner=rnd.choice(people) if rnd.random() < 0.5 else None,
                        microchip=f"643094{rnd.randint(100000000, 999999999)}"
                        if rnd.random() < 0.3 else "",
                        tattoo=f"{rnd.choice('ABCDEFGH')}{rnd.randint(1000, 9999)}"
                        if rnd.random() < 0.15 else "",
                        weight_kg=round(rnd.uniform(3.0, 9.5), 2) if rnd.random() < 0.25 else None,
                        chest_cm=round(rnd.uniform(28, 40), 1) if rnd.random() < 0.2 else None,
                        legacy_id=100_000 + counter,
                        provenance=Provenance.VERIFIED if rnd.random() < 0.25
                        else Provenance.IMPORTED,
                    )
                    counter += 1
                    made += 1
                    (males if sex == Sex.MALE else females).append(dog)
                    all_dogs.append(dog)

            prev_males, prev_females = males, females

        # Немного смертей у старших поколений.
        for dog in all_dogs[: len(all_dogs) // 4]:
            if dog.date_born and rnd.random() < 0.3:
                dog.date_died = dog.date_born + timedelta(days=rnd.randint(2500, 5500))
                dog.save(update_fields=["date_died"])

        return all_dogs

    def _titles_for_dogs(self, rnd, dogs, titles):
        for dog in dogs:
            if rnd.random() > 0.45:
                continue
            for title in rnd.sample(titles, rnd.randint(1, min(8, len(titles)))):
                DogTitle.objects.get_or_create(
                    dog=dog, title=title,
                    defaults={"year": rnd.randint(2010, 2025)},
                )

    def _registrations(self, rnd, dogs):
        for dog in dogs:
            for _ in range(rnd.choices([0, 1, 2], weights=[35, 50, 15])[0]):
                org = rnd.choice(ORGS)
                Registration.objects.get_or_create(
                    dog=dog, organisation=org,
                    number=f"{org} {rnd.randint(1000000, 9999999)}",
                )

    def _health(self, rnd, dogs, diseases):
        """
        Тестируют далеко не всех — так и в жизни. Зато у протестированных
        результаты разные, включая поражённых: карточка должна одинаково
        честно показывать и хорошую собаку, и проблемную.
        """
        for dog in dogs:
            if rnd.random() > 0.35:
                continue
            for disease in rnd.sample(diseases, rnd.randint(1, len(diseases))):
                if disease.relevant_coats and dog.coat not in disease.relevant_coats:
                    continue
                result = rnd.choices(
                    [HealthResult.CLEAR, HealthResult.CARRIER, HealthResult.AFFECTED],
                    weights=[65, 25, 10],
                )[0]
                genotype = {"clear": "N/N", "carrier": "N/L", "affected": "L/L"}[result]
                HealthTest.objects.get_or_create(
                    dog=dog, disease=disease,
                    tested_on=date(2015, 1, 1) + timedelta(days=rnd.randint(0, 3800)),
                    defaults={
                        "result": result, "genotype": genotype,
                        "lab": rnd.choice(LABS),
                        "verified": rnd.random() < 0.5,
                    },
                )

    def _coi(self, rnd, dogs):
        for dog in dogs:
            if rnd.random() > 0.7:
                continue
            Coi.objects.update_or_create(
                dog=dog,
                defaults={
                    "value": round(rnd.triangular(0, 25, 4), 3),
                    "generations": 10,
                    "known_ancestors": round(rnd.uniform(20, 100), 2),
                    "ancestor_loss": round(rnd.uniform(0, 40), 2),
                },
            )

    # --- грязь -----------------------------------------------------------

    def _dirt(self, rnd, colors):
        """
        Заведомо проблемные записи. Нужны, чтобы интерфейс проверялся
        на них с самого начала, а не после первого ETL.
        """
        cases = [
            # кличка кириллицей — проверка слага и сортировки
            dict(name="ДЛЯ ТЕБЯ ВЕЧНАЯ ЗАГАДКА ИЗ ГОРОДА ТАКС", sex=Sex.FEMALE),
            # диакритика
            dict(name="Ossa Kamenný potok", sex=Sex.FEMALE),
            # пол неизвестен, не заполнено ничего
            dict(name="Unknown dog", sex=Sex.UNKNOWN, size="", coat=""),
            # дубль клички: две разные собаки, одинаково названы
            dict(name="Fabeltier Vladimir", sex=Sex.MALE),
            dict(name="Fabeltier Vladimir", sex=Sex.MALE),
            # мусорная запись в духе легаси: пометка администратора
            # попала в поле клички
            dict(name="wrong foto", sex=Sex.UNKNOWN, size="", coat=""),
        ]
        for i, case in enumerate(cases):
            Dog.objects.create(
                slug=self._slug(case["name"], "dirt", i),
                provenance=Provenance.IMPORTED,
                legacy_id=900_000 + i,
                **case,
            )

    # --- вспомогательное -------------------------------------------------

    @staticmethod
    def _slug(name, prefix, i):
        """Кириллица через slugify даёт пустую строку — подстраховываемся."""
        base = slugify(name) or slugify(name, allow_unicode=True) or prefix
        return f"{base}-{i}"[:220]
