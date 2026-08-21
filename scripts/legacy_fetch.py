#!/usr/bin/env python3
"""
Чтение страниц легаси-сайта dachpedigrees.com.

Использовался для аудита (см. docs/legacy-audit.md) и пригодится в ETL:
функция fix() чинит смешанную кодировку, которой болеет и сайт, и, судя
по всему, будущий дамп.

Учётные данные HTTP-авторизации берутся из окружения, в репозиторий
их не кладём:

    export LEGACY_AUTH=user:password
    python scripts/legacy_fetch.py /dog/pampa-crespalia-nid/484554
"""

import html
import os
import pathlib
import re
import subprocess
import sys

BASE = os.environ.get("LEGACY_BASE", "http://www.dachpedigrees.com")
AUTH = os.environ.get("LEGACY_AUTH", "")
CACHE = pathlib.Path(os.environ.get("LEGACY_CACHE", "/tmp/legacy/cache"))


def fix(raw: bytes) -> str:
    """
    Чинит документ, в котором UTF-8 и CP1251 перемешаны побайтово.

    Сайт объявляет charset=utf-8, но часть текста лежит в CP1251, и обычный
    decode падает. Идём по байтам: сначала пробуем прочитать валидную
    UTF-8-последовательность, при неудаче трактуем один байт как CP1251.
    """
    out = bytearray()
    i = 0
    while i < len(raw):
        for length in (4, 3, 2, 1):
            try:
                raw[i:i + length].decode("utf-8")
            except UnicodeDecodeError:
                continue
            out += raw[i:i + length]
            i += length
            break
        else:
            out += raw[i:i + 1].decode("cp1251", errors="replace").encode("utf-8")
            i += 1
    return out.decode("utf-8", errors="replace")


def get(path: str) -> str:
    """Страница с диска, а при первом обращении — из сети. Кэш ради вежливости."""
    CACHE.mkdir(parents=True, exist_ok=True)
    key = CACHE / (re.sub(r"\W+", "_", path).strip("_")[:120] + ".html")
    if not key.exists():
        url = path if path.startswith("http") else BASE + path
        cmd = ["curl", "-s", "--fail-with-body"]
        if AUTH:
            cmd += ["-u", AUTH]
        result = subprocess.run(cmd + [url], capture_output=True)
        key.write_text(fix(result.stdout), encoding="utf-8")
    return key.read_text(encoding="utf-8")


def text(page: str) -> str:
    """Грубое извлечение текста: для беглого осмотра, не для разбора данных."""
    body = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", page)
    body = re.sub(r"(?s)<[^>]+>", "\n", body)
    lines = (line.strip() for line in html.unescape(body).split("\n"))
    return "\n".join(line for line in lines if len(line) > 1)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("укажите путь, например: /dog/pampa-crespalia-nid/484554")
    print(text(get(sys.argv[1])))
