import { useState } from "react";

/**
 * Демонстрационный остров. Существует только чтобы доказать,
 * что связка Django -> шаблон -> Vite -> React работает.
 * Удаляется, как только появится первый настоящий остров.
 */

type Props = {
  placeholder?: string;
  limit?: number;
};

export default function DemoSearch({ placeholder = "Поиск", limit = 10 }: Props) {
  const [query, setQuery] = useState("");

  return (
    <div>
      <input
        type="search"
        value={query}
        placeholder={placeholder}
        onChange={(event) => setQuery(event.target.value)}
      />
      <p>
        Остров смонтирован. Запрос: <strong>{query || "—"}</strong>, лимит выдачи: {limit}.
      </p>
    </div>
  );
}
