import { useCallback, useEffect, useRef, useState } from "react";

/**
 * Живой поиск по базе.
 *
 * Остров подменяет собой серверную форму и список — те остаются в HTML
 * для роботов и посетителей без JS (см. тег {% island %}).
 *
 * Что он добавляет поверх серверного варианта:
 *   - выдача обновляется по мере ввода, без перезагрузки страницы;
 *   - адрес в строке браузера меняется вместе с фильтрами, поэтому
 *     результат можно скопировать, отправить и открыть заново;
 *   - кнопка «назад» возвращает предыдущий запрос.
 *
 * Начальные данные приезжают пропсами из того же запроса, что отрисовал
 * страницу, — иначе список мигнул бы пустотой на первом кадре.
 */

type Dog = {
  name: string;
  url: string;
  sex: "male" | "female" | "unknown";
  size: string;
  coat: string;
  color: string;
  kennel: string;
  born: string | null;
  verified: boolean;
};

type Payload = {
  total: number;
  page: number;
  pages: number;
  results: Dog[];
};

type Choice = { value: string; label: string };

type Props = {
  endpoint: string;
  initial: Payload;
  query?: string;
  filters?: { size?: string; coat?: string; sex?: string };
  choices: { size: Choice[]; coat: Choice[]; sex: Choice[] };
};

const DEBOUNCE_MS = 250;

function plural(n: number, one: string, few: string, many: string): string {
  const mod100 = Math.abs(n) % 100;
  if (mod100 >= 11 && mod100 <= 14) return many;
  const mod10 = Math.abs(n) % 10;
  if (mod10 === 1) return one;
  if (mod10 >= 2 && mod10 <= 4) return few;
  return many;
}

const SEX_SIGN: Record<string, string> = { male: "♂", female: "♀", unknown: "" };

export default function DogSearch({ endpoint, initial, query = "", filters = {}, choices }: Props) {
  const [q, setQ] = useState(query);
  const [size, setSize] = useState(filters.size ?? "");
  const [coat, setCoat] = useState(filters.coat ?? "");
  const [sex, setSex] = useState(filters.sex ?? "");
  const [page, setPage] = useState(initial.page);

  const [data, setData] = useState<Payload>(initial);
  const [loading, setLoading] = useState(false);
  const [failed, setFailed] = useState(false);

  // Первый рендер уже отрисован сервером — незачем ходить за тем же самым.
  const firstRender = useRef(true);
  // Гонка ответов: медленный запрос не должен перетереть свежий.
  const requestId = useRef(0);

  const buildParams = useCallback(() => {
    const params = new URLSearchParams();
    if (q) params.set("q", q);
    if (size) params.set("size", size);
    if (coat) params.set("coat", coat);
    if (sex) params.set("sex", sex);
    if (page > 1) params.set("page", String(page));
    return params;
  }, [q, size, coat, sex, page]);

  useEffect(() => {
    if (firstRender.current) {
      firstRender.current = false;
      return;
    }

    const params = buildParams();
    const id = ++requestId.current;
    const timer = setTimeout(async () => {
      setLoading(true);
      try {
        const response = await fetch(`${endpoint}?${params}`, {
          headers: { "X-Requested-With": "fetch" },
        });
        if (!response.ok) throw new Error(String(response.status));
        const payload: Payload = await response.json();
        if (id !== requestId.current) return; // пришёл ответ на устаревший запрос
        setData(payload);
        setFailed(false);
      } catch {
        if (id === requestId.current) setFailed(true);
      } finally {
        if (id === requestId.current) setLoading(false);
      }
    }, DEBOUNCE_MS);

    return () => clearTimeout(timer);
  }, [buildParams, endpoint]);

  // Адрес идёт следом за фильтрами: ссылку на выдачу можно передать.
  useEffect(() => {
    if (firstRender.current) return;
    const params = buildParams();
    const next = params.toString() ? `?${params}` : window.location.pathname;
    window.history.replaceState(null, "", next);
  }, [buildParams]);

  function update<T>(setter: (value: T) => void) {
    return (value: T) => {
      setter(value);
      setPage(1); // смена фильтра всегда возвращает на первую страницу
    };
  }

  return (
    <div className="search-island">
      <div className="search">
        <input
          className="search__input"
          type="search"
          value={q}
          placeholder="Кличка, питомник или номер"
          onChange={(event) => update(setQ)(event.target.value)}
        />

        <select className="search__select" value={size}
                onChange={(event) => update(setSize)(event.target.value)}>
          <option value="">любой размер</option>
          {choices.size.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
        </select>

        <select className="search__select" value={coat}
                onChange={(event) => update(setCoat)(event.target.value)}>
          <option value="">любая шерсть</option>
          {choices.coat.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
        </select>

        <select className="search__select" value={sex}
                onChange={(event) => update(setSex)(event.target.value)}>
          <option value="">любой пол</option>
          {choices.sex.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
        </select>
      </div>

      <p className="search__total" aria-live="polite">
        {failed
          ? "Не удалось получить выдачу. Обновите страницу."
          : `Найдено ${data.total} ${plural(data.total, "собака", "собаки", "собак")}`}
      </p>

      <ul className={`dog-list${loading ? " dog-list--loading" : ""}`}>
        {data.results.map((dog) => (
          <li className="dog-list__row" key={dog.url}>
            <a className="dog-list__name" href={dog.url}>{dog.name}</a>
            <span className="dog-list__meta">
              {SEX_SIGN[dog.sex]} {dog.size} {dog.coat}
              {dog.color && ` · ${dog.color}`}
              {dog.born && ` · ${dog.born.slice(0, 4)}`}
              {dog.verified && <span className="dog-list__verified" title="Проверено">✓</span>}
            </span>
          </li>
        ))}
        {data.results.length === 0 && !loading && (
          <li className="dog-list__empty">Ничего не найдено.</li>
        )}
      </ul>

      {data.pages > 1 && (
        <nav className="pager">
          <button type="button" disabled={data.page <= 1}
                  onClick={() => setPage((p) => p - 1)}>← назад</button>
          <span>{data.page} из {data.pages}</span>
          <button type="button" disabled={data.page >= data.pages}
                  onClick={() => setPage((p) => p + 1)}>вперёд →</button>
        </nav>
      )}
    </div>
  );
}
