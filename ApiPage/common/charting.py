import pandas as pd


def add_time_bucket(df: pd.DataFrame, mode: str, datetime_col: str):
    """Return copied dataframe and bucket metadata for Day/Hour/Minute."""
    out = df.copy()
    if mode == "Day":
        out["TimeBucket"] = out[datetime_col].dt.strftime("%Y-%m-%d")
        return out, "TimeBucket", "Date"
    if mode == "Hour":
        out["TimeBucket"] = out[datetime_col].dt.strftime("%Y-%m-%d %H:00")
        return out, "TimeBucket", "Date-Hour"
    out["TimeBucket"] = out[datetime_col].dt.strftime("%Y-%m-%d %H:%M")
    return out, "TimeBucket", "Date-Time (Minute)"

