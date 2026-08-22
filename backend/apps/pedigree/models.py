"""
Модели предметной области.

Схема проектируется заново, а не переносится из Drupal один в один
(см. «Принципы миграции» в CLAUDE.md). Опора — обследование легаси,
docs/legacy-audit.md: там перечень исходных полей и то, что в них
намешано.

Сквозные решения:

* `legacy_id` есть почти в каждой таблице — по нему сверяются прогоны ETL
  и строятся редиректы со старых адресов вида /dog/<slug>-nid/<id>.
* `edited_fields` защищает правки людей от повторных прогонов ETL.
  Подробнее — в комментарии к LegacyMixin.
* Данные грязные по определению: почти всё допускает NULL. Схема обязана
  принять собаку, у которой известна одна кличка, и не развалиться.
"""

from django.contrib.postgres.fields import ArrayField
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.urls import reverse


class Sex(models.TextChoices):
    MALE = "male", "кобель"
    FEMALE = "female", "сука"
    UNKNOWN = "unknown", "неизвестен"


class Size(models.TextChoices):
    """Размер таксы. В легаси слит с шерстью в одну строку из 9 значений."""

    STANDARD = "standard", "стандартная"
    MINIATURE = "miniature", "карликовая"
    RABBIT = "rabbit", "кроличья"


class Coat(models.TextChoices):
    SMOOTH = "smooth", "гладкошёрстная"
    LONG = "long", "длинношёрстная"
    WIRE = "wire", "жесткошёрстная"


class Provenance(models.TextChoices):
    """
    Откуда взялась запись. Это не украшение карточки, а различие,
    на котором стоит всё преимущество перед конкурентом: полмиллиона
    записей скрейпа против наших выверенных.
    """

    IMPORTED = "imported", "импортировано из легаси"
    USER = "user", "внесено пользователем"
    VERIFIED = "verified", "проверено по документам"


class LegacyMixin(models.Model):
    """
    Общее для всего, что приезжает из Drupal.

    `edited_fields` — список имён полей, которых коснулся человек.
    ETL обязан их пропускать. Без этого первый же повторный прогон молча
    затрёт правку заводчика данными из дампа, и мы потеряем доверие
    ровно тех людей, ради которых всё затевается.

    Отсюда же следствие для эксплуатации: пока правки закрыты, дамп можно
    перезаливать сколько угодно; после открытия — только с оглядкой
    на этот список.
    """

    legacy_id = models.IntegerField(
        "идентификатор в легаси", null=True, blank=True, unique=True, db_index=True
    )
    provenance = models.CharField(
        "происхождение", max_length=16, choices=Provenance, default=Provenance.USER
    )
    edited_fields = ArrayField(
        models.CharField(max_length=64),
        verbose_name="поля, правленные вручную",
        default=list,
        blank=True,
    )
    created_at = models.DateTimeField("создано", auto_now_add=True)
    updated_at = models.DateTimeField("изменено", auto_now=True)

    class Meta:
        abstract = True


# --- Справочники ---------------------------------------------------------


class Country(models.Model):
    code = models.CharField("код ISO", max_length=2, primary_key=True)
    name = models.CharField("название", max_length=100)

    class Meta:
        verbose_name = "страна"
        verbose_name_plural = "страны"
        ordering = ["name"]

    def __str__(self):
        return self.name


class TitleKind(models.TextChoices):
    """В легаси титулы разложены по трём разным полям — сохраняем различие."""

    SHOW = "show", "выставочный"
    FIELD = "field", "полевые испытания"
    OTHER = "other", "прочий"


class Title(models.Model):
    """
    Справочник титулов. В легаси это список из 121 аббревиатуры,
    выгружен в docs/legacy/titles.txt. Страна зашита в саму аббревиатуру
    (RKFCH — Россия, BLRCH — Беларусь), поэтому вынесена отдельным полем.
    """

    code = models.CharField("аббревиатура", max_length=32, unique=True)
    name = models.CharField("расшифровка", max_length=200, blank=True)
    kind = models.CharField("тип", max_length=8, choices=TitleKind, default=TitleKind.SHOW)
    country = models.ForeignKey(
        Country, verbose_name="страна", null=True, blank=True, on_delete=models.SET_NULL
    )

    class Meta:
        verbose_name = "титул"
        verbose_name_plural = "титулы"
        ordering = ["code"]

    def __str__(self):
        return self.code


class Color(models.Model):
    """
    Нормализованный окрас.

    В легаси это свободный текст вразнобой: `black&tan`, `brown&tan`,
    `Chocolate & Tan Dapple`, `Creamy Red`. Исходная строка сохраняется
    в Dog.color_raw, сюда попадает результат разбора.

    `is_dapple` вынесен отдельно не ради красоты: дапл — это локус M,
    и вязка дапл x дапл даёт 25% гомозигот с глухотой и слепотой.
    То есть часть данных для модуля здоровья уже лежит в старой базе,
    просто внутри строки окраса.
    """

    name = models.CharField("название", max_length=100, unique=True)
    is_dapple = models.BooleanField("дапл (локус M)", default=False)
    is_double_dapple = models.BooleanField("двойной дапл", default=False)

    class Meta:
        verbose_name = "окрас"
        verbose_name_plural = "окрасы"
        ordering = ["name"]

    def __str__(self):
        return self.name


# --- Люди и питомники ----------------------------------------------------


class Kennel(LegacyMixin):
    name = models.CharField("название", max_length=200)
    country = models.ForeignKey(
        Country, verbose_name="страна", null=True, blank=True, on_delete=models.SET_NULL
    )
    slug = models.SlugField("адрес", max_length=220, unique=True)

    class Meta:
        verbose_name = "питомник"
        verbose_name_plural = "питомники"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Person(LegacyMixin):
    """
    Заводчик или владелец.

    В легаси одна и та же сущность хранится двумя способами: ссылкой
    на ноду ownerbreeder и отдельно свободным текстом «когда его нет
    в базе» (field_breeder_not_db). ETL сливает оба в эту таблицу,
    исходная строка остаётся в raw_name для разбора и сверки.
    """

    name = models.CharField("имя", max_length=200)
    raw_name = models.TextField("как записано в легаси", blank=True)
    kennel = models.ForeignKey(
        Kennel, verbose_name="питомник", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="people",
    )
    country = models.ForeignKey(
        Country, verbose_name="страна", null=True, blank=True, on_delete=models.SET_NULL
    )
    slug = models.SlugField("адрес", max_length=220, unique=True)

    class Meta:
        verbose_name = "человек"
        verbose_name_plural = "люди"
        ordering = ["name"]

    def __str__(self):
        return self.name


# --- Собака --------------------------------------------------------------


class Dog(LegacyMixin):
    name = models.CharField("кличка", max_length=200)
    # Домашняя кличка: в легаси field_home_name, на старом сайте
    # показывается в скобках. Заводчики ей активно пользуются.
    home_name = models.CharField("домашняя кличка", max_length=100, blank=True)
    slug = models.SlugField("адрес", max_length=220, unique=True)

    sex = models.CharField("пол", max_length=8, choices=Sex, default=Sex.UNKNOWN)
    size = models.CharField("размер", max_length=10, choices=Size, blank=True)
    coat = models.CharField("шерсть", max_length=8, choices=Coat, blank=True)

    color = models.ForeignKey(
        Color, verbose_name="окрас", null=True, blank=True, on_delete=models.SET_NULL
    )
    color_raw = models.CharField("окрас как в легаси", max_length=200, blank=True)

    date_born = models.DateField("дата рождения", null=True, blank=True)
    date_died = models.DateField("дата смерти", null=True, blank=True)
    # Даты в легаси бывают неполными и в свободной форме. Разобранное
    # кладём в поля выше, исходную строку не выбрасываем.
    date_born_raw = models.CharField("дата рождения как в легаси", max_length=100, blank=True)

    # Родители. SET_NULL, потому что удаление дубля не должно уносить
    # с собой полродословной. Циклы в предках база не запретит —
    # проверка на уровне приложения плюс защита от зацикливания
    # в рекурсивном CTE.
    sire = models.ForeignKey(
        "self", verbose_name="отец", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="offspring_as_sire",
        limit_choices_to={"sex": Sex.MALE},
    )
    dam = models.ForeignKey(
        "self", verbose_name="мать", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="offspring_as_dam",
        limit_choices_to={"sex": Sex.FEMALE},
    )

    breeder = models.ForeignKey(
        Person, verbose_name="заводчик", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="bred_dogs",
    )
    owner = models.ForeignKey(
        Person, verbose_name="владелец", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="owned_dogs",
    )
    kennel = models.ForeignKey(
        Kennel, verbose_name="питомник", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="dogs",
    )

    # В легаси клеймо и микрочип свалены в одно поле field_tatoo
    # с подписью «Tatoo/Microchip». Разделяем: чип — 15 цифр,
    # клеймо — буквы с цифрами.
    microchip = models.CharField("микрочип", max_length=20, blank=True, db_index=True)
    tattoo = models.CharField("клеймо", max_length=40, blank=True, db_index=True)

    weight_kg = models.DecimalField(
        "вес, кг", max_digits=4, decimal_places=2, null=True, blank=True
    )
    chest_cm = models.DecimalField(
        "обхват груди, см", max_digits=4, decimal_places=1, null=True, blank=True
    )

    titles = models.ManyToManyField(
        Title, verbose_name="титулы", through="DogTitle", related_name="dogs", blank=True
    )

    # Помёт, в котором собака родилась. Однопомётники берутся отсюда.
    litter = models.ForeignKey(
        "Litter", verbose_name="помёт", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="puppies",
    )

    notes = models.TextField("примечания", blank=True)

    class Meta:
        verbose_name = "собака"
        verbose_name_plural = "собаки"
        ordering = ["name"]
        indexes = [
            models.Index(fields=["size", "coat"]),
            models.Index(fields=["date_born"]),
        ]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("pedigree:dog-detail", args=[self.slug])


class DogTitle(models.Model):
    """Связка собаки с титулом. Год нужен, порядок в карточке — по нему."""

    dog = models.ForeignKey(Dog, on_delete=models.CASCADE, related_name="dog_titles")
    title = models.ForeignKey(Title, on_delete=models.CASCADE)
    year = models.PositiveSmallIntegerField("год", null=True, blank=True)

    class Meta:
        verbose_name = "титул собаки"
        verbose_name_plural = "титулы собаки"
        constraints = [
            models.UniqueConstraint(fields=["dog", "title"], name="uniq_dog_title"),
        ]

    def __str__(self):
        return f"{self.dog} — {self.title}"


class Registration(models.Model):
    """
    Регистрационный номер. Их у собаки может быть несколько — разные
    кинологические организации разных стран. В легаси поле одно,
    кратность уточняется по дампу.
    """

    dog = models.ForeignKey(Dog, on_delete=models.CASCADE, related_name="registrations")
    organisation = models.CharField("организация", max_length=100)
    number = models.CharField("номер", max_length=100, db_index=True)

    class Meta:
        verbose_name = "регистрация"
        verbose_name_plural = "регистрации"
        constraints = [
            models.UniqueConstraint(
                fields=["dog", "organisation", "number"], name="uniq_dog_registration"
            ),
        ]

    def __str__(self):
        return f"{self.organisation} {self.number}"


class Litter(LegacyMixin):
    sire = models.ForeignKey(
        Dog, verbose_name="отец", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="litters_as_sire",
    )
    dam = models.ForeignKey(
        Dog, verbose_name="мать", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="litters_as_dam",
    )
    date_born = models.DateField("дата рождения", null=True, blank=True)
    kennel = models.ForeignKey(
        Kennel, verbose_name="питомник", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="litters",
    )
    letter = models.CharField("буква помёта", max_length=8, blank=True)

    class Meta:
        verbose_name = "помёт"
        verbose_name_plural = "помёты"
        ordering = ["-date_born"]

    def __str__(self):
        return f"помёт от {self.date_born or '?'}"


class Photo(models.Model):
    dog = models.ForeignKey(Dog, on_delete=models.CASCADE, related_name="photos")
    image = models.ImageField("файл", upload_to="dogs/%Y/%m")
    caption = models.CharField("подпись", max_length=200, blank=True)
    is_primary = models.BooleanField("основное", default=False)
    order = models.PositiveSmallIntegerField("порядок", default=0)

    class Meta:
        verbose_name = "фотография"
        verbose_name_plural = "фотографии"
        ordering = ["-is_primary", "order"]


# --- Здоровье ------------------------------------------------------------


class Disease(models.Model):
    """
    Справочник заболеваний и тестов.

    Главный дифференциатор проекта: у конкурента здоровья нет вообще,
    а для таксы это основная тема. Ключевые: IVDD (дископатия),
    болезнь Лафоры у жесткошёрстных кроличьих, cord1/PRA, вывих
    коленной чашечки, локус M.
    """

    code = models.SlugField("код", max_length=50, unique=True)
    name = models.CharField("название", max_length=200)
    gene = models.CharField("ген или локус", max_length=50, blank=True)
    description = models.TextField("описание", blank=True)
    # Для скольких разновидностей актуально: Лафора — почти только
    # у жесткошёрстных кроличьих, cord1 — у гладких и длинных.
    relevant_coats = ArrayField(
        models.CharField(max_length=8, choices=Coat),
        verbose_name="актуально для шерсти", default=list, blank=True,
    )

    class Meta:
        verbose_name = "заболевание"
        verbose_name_plural = "заболевания"
        ordering = ["name"]

    def __str__(self):
        return self.name


class HealthResult(models.TextChoices):
    CLEAR = "clear", "чист"
    CARRIER = "carrier", "носитель"
    AFFECTED = "affected", "поражён"
    UNKNOWN = "unknown", "не тестирован"


class HealthTest(models.Model):
    dog = models.ForeignKey(Dog, on_delete=models.CASCADE, related_name="health_tests")
    disease = models.ForeignKey(Disease, on_delete=models.PROTECT, related_name="tests")
    result = models.CharField(
        "результат", max_length=10, choices=HealthResult, default=HealthResult.UNKNOWN
    )
    genotype = models.CharField("генотип", max_length=30, blank=True)
    lab = models.CharField("лаборатория", max_length=120, blank=True)
    tested_on = models.DateField("дата теста", null=True, blank=True)
    # Скан документа — то, чем наши записи отличаются от скрейпа.
    document = models.FileField("документ", upload_to="health/%Y/%m", blank=True)
    verified = models.BooleanField("подтверждено по документу", default=False)

    class Meta:
        verbose_name = "тест здоровья"
        verbose_name_plural = "тесты здоровья"
        ordering = ["disease__name"]
        constraints = [
            models.UniqueConstraint(
                fields=["dog", "disease", "tested_on"], name="uniq_dog_disease_date"
            ),
        ]

    def __str__(self):
        return f"{self.dog} — {self.disease}: {self.get_result_display()}"


# --- Инбридинг -----------------------------------------------------------


class Coi(models.Model):
    """
    Коэффициент инбридинга.

    Считается ночной задачей Celery по 10 поколениям и складывается сюда
    с отметкой времени. На лету не считать — на 50 000 собак это дорого.
    """

    dog = models.OneToOneField(Dog, on_delete=models.CASCADE, related_name="coi")
    value = models.DecimalField(
        "COI, %", max_digits=6, decimal_places=3,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    generations = models.PositiveSmallIntegerField("поколений", default=10)
    known_ancestors = models.DecimalField(
        "известно предков, %", max_digits=5, decimal_places=2, null=True, blank=True
    )
    ancestor_loss = models.DecimalField(
        "ancestor loss, %", max_digits=5, decimal_places=2, null=True, blank=True
    )
    calculated_at = models.DateTimeField("рассчитано", auto_now=True)

    class Meta:
        verbose_name = "коэффициент инбридинга"
        verbose_name_plural = "коэффициенты инбридинга"

    def __str__(self):
        return f"{self.dog}: {self.value}%"
