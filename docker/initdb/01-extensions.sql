-- Расширения Postgres, нужные проекту. Выполняется один раз при создании тома.
-- pg_trgm  — нечёткий поиск по кличкам (опечатки, транслитерация)
-- unaccent — поиск без учёта диакритики: HÄLLUDDEN'S найдётся по "HALLUDDENS"
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS unaccent;
CREATE EXTENSION IF NOT EXISTS btree_gin;
