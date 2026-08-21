import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { islands } from "./registry";

// Токены и базовые стили: нужны на каждой странице, поэтому висят на входе,
// а не на конкретном острове. Vite вынесет их в отдельный CSS-файл манифеста.
import "./styles/tokens.css";
import "./styles/base.css";
import "./styles/dog-card.css";

/**
 * Точка входа островного режима.
 *
 * Django рендерит страницу целиком, а этот скрипт находит в готовом HTML
 * контейнеры <div data-island="..." data-props="..."> и монтирует в них
 * React-компоненты. Всё остальное на странице остаётся серверным HTML —
 * это то, что нужно для SEO справочника.
 */

function parseProps(element: HTMLElement): Record<string, unknown> {
  const raw = element.dataset.props;
  if (!raw) return {};
  try {
    return JSON.parse(raw) as Record<string, unknown>;
  } catch (error) {
    console.error(`Остров "${element.dataset.island}": не разобрать data-props`, error);
    return {};
  }
}

async function mountIsland(element: HTMLElement): Promise<void> {
  const name = element.dataset.island;
  if (!name) return;

  const loader = islands[name];
  if (!loader) {
    console.error(`Остров "${name}" не найден в реестре (src/registry.ts)`);
    return;
  }

  // помечаем сразу, чтобы повторный вызов не смонтировал остров дважды
  if (element.dataset.islandMounted === "true") return;
  element.dataset.islandMounted = "true";

  try {
    const { default: Component } = await loader();
    createRoot(element).render(
      <StrictMode>
        <Component {...parseProps(element)} />
      </StrictMode>,
    );
  } catch (error) {
    element.dataset.islandMounted = "false";
    console.error(`Остров "${name}": ошибка загрузки`, error);
  }
}

export function mountAll(root: ParentNode = document): void {
  root.querySelectorAll<HTMLElement>("[data-island]").forEach((element) => {
    void mountIsland(element);
  });
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", () => mountAll());
} else {
  mountAll();
}
