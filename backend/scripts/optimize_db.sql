-- Обслуговування БД після масового наповнення (лаба 7). Виконати один раз:
--   psql "$DATABASE_URL_SYNC" -f backend/scripts/optimize_db.sql
-- CLUSTER фізично впорядковує рядки за GiST-індексом: сусідні за координатами укриття
-- лежать в сусідніх сторінках, тому геопошук читає менше блоків.
CLUSTER places USING idx_places_location;
ANALYZE places;
