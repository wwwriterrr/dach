# syntax=docker/dockerfile:1
# Только для разработки: Vite dev-server с HMR.
# В продакшне фронтенд собирается первой стадией backend/Dockerfile,
# и Node в рантайме не участвует.
FROM node:22-alpine

WORKDIR /app/frontend

COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install

COPY frontend ./

EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
