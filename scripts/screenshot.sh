#!/usr/bin/env bash
# Снимок страницы стенда в PNG.
#
# Браузера в системе нет и не нужно: берём одноразовый контейнер,
# машина остаётся чистой. Смотреть готовые файлы удобно прямо
# из VS Code по Remote-SSH.
#
#   scripts/screenshot.sh /dogs/ list
#   scripts/screenshot.sh "/dog/some-slug/?generations=5" ped5 1400 2600 0.7
#
# Пятый аргумент — масштаб. Кадр выше ~2600 пикселей уронит GPU-процесс
# (предел размера сообщения при копировании буфера), поэтому длинные
# страницы снимаются уменьшенным масштабом, а не увеличенной высотой.
set -euo pipefail

PATH_PART="${1:?укажите путь, например /dogs/}"
NAME="${2:-shot}"
WIDTH="${3:-1400}"
HEIGHT="${4:-2600}"
SCALE="${5:-1}"

if [ "${HEIGHT}" -gt 2600 ]; then
  echo "предупреждение: высота больше 2600 роняет GPU-процесс, уменьшите масштабом" >&2
fi

OUT_DIR="$(cd "$(dirname "$0")/.." && pwd)/var/shots"
mkdir -p "$OUT_DIR"
chmod 777 "$OUT_DIR"

docker run --rm --network host -v "$OUT_DIR:/shots" \
  --entrypoint chromium-browser zenika/alpine-chrome \
  --headless --no-sandbox --disable-gpu --hide-scrollbars \
  --window-size="${WIDTH},${HEIGHT}" \
  --force-device-scale-factor="${SCALE}" \
  --virtual-time-budget=6000 \
  --screenshot="/shots/${NAME}.png" \
  "http://127.0.0.1:8000${PATH_PART}" 2>&1 | grep -viE 'bluez|runtime_features|Floss|policy' >&2 || true

echo "готово: var/shots/${NAME}.png"
