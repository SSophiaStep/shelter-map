-- Наповнення БД тестовими даними: 100 000 об'єктів навколо 8 великих міст України
INSERT INTO places (name, type, address, capacity, is_available, location)
SELECT
    'Об''єкт ' || g,
    CASE WHEN random() < 0.7 THEN 'SHELTER'::placetype ELSE 'HEATING'::placetype END,
    'вул. Тестова, ' || (g % 200),
    (random() * 500)::int,
    random() < 0.9,
    ST_SetSRID(
        ST_MakePoint(
            (ARRAY[30.5234, 24.0297, 30.7233, 36.2304, 35.0462, 25.9403, 22.2879, 31.2893])[1 + (g % 8)]
                + (random() - 0.5) * 0.3,
            (ARRAY[50.4501, 49.8397, 46.4825, 49.9935, 48.4647, 48.2915, 48.6208, 51.4982])[1 + (g % 8)]
                + (random() - 0.5) * 0.2
        ),
        4326
    )::geography
FROM generate_series(1, 100000) AS g;

ANALYZE places;
