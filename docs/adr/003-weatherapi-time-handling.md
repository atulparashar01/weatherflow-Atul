# ADR 003: WeatherAPI time is read from `time_epoch` and stored as UTC

Status: Accepted

## Context

WeatherAPI gives two time fields for each forecast hour: `time_epoch` and `time`. Its
documentation describes `time_epoch` only as "Time as an epoch value" and `time` as "Date and
time", and does not say which timezone either one uses.

The warehouse stores every observation as an exact instant in UTC (`observed_at_utc`) and
derives the London date (`date_id`) and hour (`hour_local`) from it. If the WeatherAPI time were
read in the wrong timezone, its rows would sit 1 hour off in summer (British Summer Time), or
several hours off for a city in another timezone. The cross-source check (Open-Meteo against
WeatherAPI) would then compare different hours and report differences that are not real.

## Decision

Read `time_epoch` as Unix seconds and convert it with `pd.to_datetime(..., unit="s", utc=True)`.
That value becomes `observed_at_utc`. The text field `time` is not used to build the stored time.
London local time is derived from the UTC value with the `Europe/London` timezone, as for
Open-Meteo, so British Summer Time is handled in one place.

How I checked it: for one sample hour I converted `time_epoch` into the timezone named in the
response (`location.tz_id`) and compared the result with the `time` text. They gave the same clock
time, so `time` is the local time of the city and `time_epoch` is the real instant. I repeated the
check with a city outside the UK (New York) to make sure the code does not quietly assume London.

## Consequences

- Every WeatherAPI row has an unambiguous UTC time, and both sources line up on the same UTC hour,
  so the cross-source temperature check compares like with like.
- Clock changes are safe. An epoch value has no repeated or missing hour, which a local time string
  does have when the clocks go back or forward.
- The code depends on WeatherAPI continuing to supply `time_epoch`. If the field changed, the
  `test_normalise_weatherapi` tests would fail first.

## Alternatives considered

- **Read `time` as if it were UTC.** Simple, but wrong: it is local time, so rows would be one hour
  off in summer for the UK, and more for other cities.
- **Read `time` as London time.** Correct for the five UK cities today, but it breaks as soon as a
  city in another timezone is added. It also cannot tell the two 01:00 hours apart on the night the
  clocks go back.
- **Read `time` with the response's `tz_id`.** Correct in most hours, but it still has the repeated
  hour problem in October, and it needs more code than using the epoch value.
