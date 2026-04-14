import pandas as pd


# Fonte oficial:
# - Calendário do mercado 2024/2025/2026 da B3
# - https://www.b3.com.br/pt_br/solucoes/plataformas/puma-trading-system/para-participantes-e-traders/calendario-de-negociacao/feriados/
#
# Lista restrita aos anos cobertos pela base do case e aos dias sem pregão para o mercado listado.
B3_TRADING_HOLIDAYS = {
    2024: {
        "2024-01-01",
        "2024-02-12",
        "2024-02-13",
        "2024-03-29",
        "2024-05-01",
        "2024-05-30",
        "2024-11-15",
        "2024-11-20",
        "2024-12-24",
        "2024-12-25",
        "2024-12-31",
    },
    2025: {
        "2025-01-01",
        "2025-03-03",
        "2025-03-04",
        "2025-04-18",
        "2025-04-21",
        "2025-05-01",
        "2025-06-19",
        "2025-11-20",
        "2025-12-24",
        "2025-12-25",
        "2025-12-31",
    },
    2026: {
        "2026-01-01",
        "2026-02-16",
        "2026-02-17",
        "2026-04-03",
        "2026-04-21",
        "2026-05-01",
        "2026-06-04",
        "2026-09-07",
        "2026-10-12",
        "2026-11-02",
        "2026-11-20",
        "2026-12-24",
        "2026-12-25",
        "2026-12-31",
    },
}


def holiday_index_between(start_date, end_date):
    start_ts = pd.Timestamp(start_date)
    end_ts = pd.Timestamp(end_date)
    holidays = []
    for year in range(start_ts.year, end_ts.year + 1):
        for holiday in sorted(B3_TRADING_HOLIDAYS.get(year, set())):
            holiday_ts = pd.Timestamp(holiday)
            if start_ts <= holiday_ts <= end_ts:
                holidays.append(holiday_ts)
    return pd.DatetimeIndex(sorted(holidays))


def business_days_between(start_date, end_date):
    start_ts = pd.Timestamp(start_date)
    end_ts = pd.Timestamp(end_date)
    if pd.isna(start_ts) or pd.isna(end_ts) or end_ts < start_ts:
        return pd.DatetimeIndex([])
    holidays = holiday_index_between(start_ts, end_ts)
    return pd.bdate_range(start=start_ts, end=end_ts, freq="C", holidays=holidays)


def is_business_day(series):
    series = pd.to_datetime(series)
    holidays = set(holiday_index_between(series.min(), series.max()))
    weekdays = series.dt.weekday < 5
    not_holiday = ~series.isin(holidays)
    return weekdays & not_holiday
