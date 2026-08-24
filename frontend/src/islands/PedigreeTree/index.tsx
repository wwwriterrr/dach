import { useCallback, useEffect, useRef, useState } from "react";

/**
 * Дерево родословной.
 *
 * Серверный вариант (шаблон _pedigree.html) уже рисует то же дерево
 * ссылками и переключает глубину обычным GET — он остаётся в HTML
 * для роботов и посетителей без JS. Остров добавляет три вещи,
 * которых без скриптов не сделать:
 *
 *   1. Глубина 3/4/5 переключается без перезагрузки.
 *   2. Наведение на повторяющегося предка подсвечивает все его
 *      вхождения разом. В инбредной родословной одна и та же собака
 *      встречается до пяти раз в разных ветвях, и глазами их не свести.
 *   3. Клик по ячейке перестраивает дерево от этого предка. Обычно
 *      обход родословной вглубь — это цепочка переходов по страницам;
 *      здесь предок становится корнем на месте, с возвратом назад.
 *
 * Клик по самой кличке остаётся обычным переходом на карточку —
 * ломать ожидание от ссылки нельзя.
 */

type Node = {
  position: number;
  generation: number;
  col: number;
  row_start: number;
  row_span: number;
  dog: {
    id: number;
    name: string;
    slug: string;
    url: string;
    sex: "male" | "female" | "unknown";
    color: string;
    born: number | null;
    titles: string[];
    photo: string | null;
    health: "clear" | "carrier" | "affected" | null;
    repeat: number;
    repeat_level: number | null;
  } | null;
};

type Tree = {
  root: { name: string; slug: string; url: string };
  generations: number;
  total_rows: number;
  nodes: Node[];
  known: number;
  possible: number;
  completeness: number;
  repeats: Record<string, number>;
};

type Props = {
  endpoint: string;
  depths: number[];
  initial: Tree;
};

const HEALTH_TITLE: Record<string, string> = {
  clear: "тесты чистые",
  carrier: "носитель",
  affected: "поражён",
};

export default function PedigreeTree({ endpoint, depths, initial }: Props) {
  const [tree, setTree] = useState<Tree>(initial);
  const [depth, setDepth] = useState(initial.generations);
  const [rootSlug, setRootSlug] = useState(initial.root.slug);
  const [hovered, setHovered] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);

  // Куда возвращаться после прогулки по предкам.
  const homeRoot = useRef(initial.root);
  const firstRender = useRef(true);
  const requestId = useRef(0);

  const load = useCallback(async (slug: string, generations: number) => {
    const id = ++requestId.current;
    setLoading(true);
    try {
      // Адрес собран из шаблона: подменяем в нём слаг корня.
      const url = endpoint.replace(homeRoot.current.slug, slug);
      const response = await fetch(`${url}?generations=${generations}`);
      if (!response.ok) throw new Error(String(response.status));
      const payload: Tree = await response.json();
      if (id === requestId.current) setTree(payload);
    } catch {
      /* оставляем предыдущее дерево: пустой экран хуже устаревшего */
    } finally {
      if (id === requestId.current) setLoading(false);
    }
  }, [endpoint]);

  useEffect(() => {
    if (firstRender.current) {
      firstRender.current = false;
      return;
    }
    void load(rootSlug, depth);
  }, [rootSlug, depth, load]);

  const isHome = rootSlug === homeRoot.current.slug;

  return (
    <div className="pedigree-block">
      <div className="pedigree-block__head">
        <h2 className="section-title">Родословная</h2>

        <div className="pedigree-block__tools">
          <span className="pedigree-block__label">поколений:</span>
          {depths.map((value) => (
            <button
              key={value}
              type="button"
              className={`depth-switch${value === tree.generations ? " depth-switch--active" : ""}`}
              onClick={() => setDepth(value)}
            >
              {value}
            </button>
          ))}
        </div>
      </div>

      <p className="pedigree-block__stats">
        {!isHome && (
          <>
            <button type="button" className="pedigree-block__back"
                    onClick={() => setRootSlug(homeRoot.current.slug)}>
              ← к {homeRoot.current.name}
            </button>
            {" · "}
          </>
        )}
        Известно {tree.known} из {tree.possible} предков —{" "}
        <strong>{tree.completeness}%</strong>
      </p>

      <div className="pedigree-scroll">
        <div
          className={`pedigree${loading ? " pedigree--loading" : ""}`}
          style={{
            ["--generations" as string]: tree.generations + 1,
            ["--rows" as string]: tree.total_rows,
          }}
        >
          {tree.nodes.map((node) => {
            const dog = node.dog;
            const linked = dog !== null && hovered !== null && dog.id === hovered;

            const classes = ["pedigree__cell"];
            if (!dog) classes.push("pedigree__cell--empty");
            if (dog?.repeat_level) {
              classes.push(`pedigree__cell--repeat-${dog.sex}-${dog.repeat_level}`);
            }
            if (linked) classes.push("pedigree__cell--linked");

            return (
              <div
                key={node.position}
                className={classes.join(" ")}
                style={{
                  ["--col" as string]: node.col,
                  ["--row" as string]: node.row_start,
                  ["--span" as string]: node.row_span,
                }}
                onMouseEnter={() => dog && setHovered(dog.id)}
                onMouseLeave={() => setHovered(null)}
                onClick={(event) => {
                  // Клик по кличке — обычный переход, не перехватываем.
                  if ((event.target as HTMLElement).closest("a")) return;
                  if (dog && dog.slug !== rootSlug) setRootSlug(dog.slug);
                }}
                title={dog && dog.slug !== rootSlug ? "построить дерево от этой собаки" : undefined}
              >
                {dog ? (
                  <>
                    {/* Фото только там, где ячейка достаточно высокая:
                        в последнем поколении она в одну строку. */}
                    {dog.photo && node.row_span >= 2 && (
                      <img className="pedigree__photo" src={dog.photo}
                           alt="" loading="lazy" width={44} height={33} />
                    )}

                    <div className="pedigree__body">
                      <a className="pedigree__name" href={dog.url}>{dog.name}</a>

                      {dog.titles.length > 0 && (
                        <div className="pedigree__titles">{dog.titles.join(", ")}</div>
                      )}

                      <div className="pedigree__meta">
                        {dog.color}
                        {dog.born ? ` · ${dog.born}` : ""}
                      </div>
                    </div>

                    {dog.repeat_level && (
                      <span className="pedigree__repeat"
                            title={`встречается в родословной ${dog.repeat} раза`}>
                        ×{dog.repeat}
                      </span>
                    )}

                    {dog.health && (
                      <span className={`pedigree__health pedigree__health--${dog.health}`}
                            title={HEALTH_TITLE[dog.health]} />
                    )}
                  </>
                ) : (
                  <span className="pedigree__unknown">неизвестен</span>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {Object.keys(tree.repeats).length > 0 && (
        <ul className="pedigree-legend">
          {(["male", "female"] as const).map((sex) =>
            [2, 3, 4].map((level) => (
              <li key={`${sex}-${level}`}>
                <span className={`pedigree-legend__swatch pedigree-legend__swatch--${sex}-${level}`} />
                {sex === "male" ? "кобель" : "сука"}{" "}
                {level === 2 ? "дважды" : level === 3 ? "трижды" : "четырежды и чаще"}
              </li>
            )),
          )}
        </ul>
      )}
    </div>
  );
}
