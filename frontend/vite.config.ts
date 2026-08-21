import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { resolve } from "node:path";

// Собранный бандл кладём туда, где его ждёт Django (STATICFILES_DIRS в base.py).
const DJANGO_STATIC_SRC = resolve(__dirname, "../backend/frontend_dist");

export default defineConfig({
  plugins: [react()],
  base: "/static/",
  build: {
    outDir: DJANGO_STATIC_SRC,
    emptyOutDir: true,
    manifest: true,
    rollupOptions: {
      // Единая точка входа: она сама находит острова в разметке и грузит их
      // по требованию, поэтому неиспользуемый на странице код не скачивается.
      input: resolve(__dirname, "src/main.tsx"),
    },
  },
  server: {
    host: "0.0.0.0",
    port: 5173,
    // в контейнере файловые события не всегда доходят — включаем опрос
    watch: { usePolling: true },
    // Django отдаёт страницу, Vite — только ассеты; CORS нужен для dev-режима
    cors: true,
  },
  resolve: {
    alias: { "@": resolve(__dirname, "src") },
  },
});
