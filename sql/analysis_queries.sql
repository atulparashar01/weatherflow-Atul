-- WeatherFlow analysis queries (PostgreSQL, star schema)
-- Tables: fact_weather_hourly (f), dim_city (c), dim_date (d)
-- Each source is stored separately: add  WHERE f.source = 'open_meteo_forecast'  to look at one source only.

-- 1. Do we have data for every city, and what time range does it cover?
--    (JOIN: dim_city gives the city name)
SELECT c.city_name,
       COUNT(*)                AS row_count,
       MIN(f.observed_at_utc)  AS first_hour_utc,
       MAX(f.observed_at_utc)  AS last_hour_utc
FROM fact_weather_hourly AS f
JOIN dim_city AS c ON c.city_id = f.city_id
GROUP BY c.city_name
ORDER BY c.city_name;

-- 2. How warm was each city yesterday (London date) on average?
--    (JOINS: dim_city for the name, dim_date for the calendar day)
SELECT c.city_name,
       ROUND(AVG(f.temperature_c)::numeric, 1) AS avg_temp_c
FROM fact_weather_hourly AS f
JOIN dim_city AS c ON c.city_id = f.city_id
JOIN dim_date AS d ON d.date_id = f.date_id
WHERE d.full_date = (now() AT TIME ZONE 'Europe/London')::date - 1
GROUP BY c.city_name
ORDER BY avg_temp_c DESC;

-- 3. When and where was it windiest (riskiest for outdoor setups)?
--    (JOINS: city name and London date)
SELECT c.city_name,
       d.full_date,
       f.hour_local,
       f.wind_speed_kmh,
       f.beaufort_scale
FROM fact_weather_hourly AS f
JOIN dim_city AS c ON c.city_id = f.city_id
JOIN dim_date AS d ON d.date_id = f.date_id
ORDER BY f.wind_speed_kmh DESC
LIMIT 5;

-- 4. Average wind by city on weekends vs weekdays
--    (JOINS: dim_city and dim_date.is_weekend)
SELECT c.city_name,
       CASE WHEN d.is_weekend THEN 'weekend' ELSE 'weekday' END AS day_type,
       ROUND(AVG(f.wind_speed_kmh)::numeric, 1)                  AS avg_wind_kmh,
       COUNT(*)                                                  AS hours
FROM fact_weather_hourly AS f
JOIN dim_city AS c ON c.city_id = f.city_id
JOIN dim_date AS d ON d.date_id = f.date_id
GROUP BY c.city_name, d.is_weekend
ORDER BY c.city_name, d.is_weekend;

-- 5. How many hours of each outdoor-work risk level does each city have?
--    (JOIN: dim_city)
SELECT c.city_name,
       COUNT(*) FILTER (WHERE f.outdoor_work_risk = 'high')   AS high_hours,
       COUNT(*) FILTER (WHERE f.outdoor_work_risk = 'medium') AS medium_hours,
       COUNT(*) FILTER (WHERE f.outdoor_work_risk = 'low')    AS low_hours,
       ROUND(100.0 * COUNT(*) FILTER (WHERE f.outdoor_work_risk = 'high') / COUNT(*), 1) AS pct_high
FROM fact_weather_hourly AS f
JOIN dim_city AS c ON c.city_id = f.city_id
GROUP BY c.city_name
ORDER BY pct_high DESC;