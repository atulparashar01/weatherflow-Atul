-- 1. Business question: do we have data for every city, and what time range does it cover?
SELECT city, COUNT(*) AS row_count,
       MIN(observed_at) AS first_hour, MAX(observed_at) AS last_hour
FROM weather_hourly
GROUP BY city;

-- 2. Business question: how warm was each city yesterday on average?
SELECT city, ROUND(AVG(temperature_c), 1) AS avg_temp_c
FROM weather_hourly
WHERE date(observed_at) = date('now', '-1 day')
GROUP BY city;

-- 3. Business question: when and where was it windiest (riskiest for outdoor setups)?
SELECT city, observed_at, wind_speed_kmh
FROM weather_hourly
ORDER BY wind_speed_kmh DESC
LIMIT 5;