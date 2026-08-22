import type { ComponentType } from "react";

/**
 * Реестр островов.
 *
 * Ключ — то, что пишется в шаблоне: {% island "dog-search" %}.
 * Значение — динамический импорт, благодаря которому Vite режет бандл
 * на части и страница грузит только те острова, которые на ней есть.
 *
 * Новый остров добавляется одной строкой сюда.
 */
export const islands: Record<string, () => Promise<{ default: ComponentType<any> }>> = {
  "dog-search": () => import("./islands/DogSearch"),
};

export type IslandName = keyof typeof islands;
