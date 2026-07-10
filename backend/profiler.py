import pandas as pd


def profile_dataframe(df):
    profiles = []
    for col in df.columns:
        missing_count = int(df[col].isna().sum())
        unique_count = int(df[col].nunique())
        total_rows = df.shape[0]

        profile = {
            "name": col,
            "missing": {
                "count": missing_count,
                "percentage": round(missing_count * 100 / total_rows, 2),
            },
            "uniqueness": {
                "count": unique_count,
                "ratio": round(unique_count * 100 / total_rows, 2),
            },
        }

        if pd.api.types.is_bool_dtype(df[col]):
            profile["type"] = "boolean"
        elif pd.api.types.is_numeric_dtype(df[col]):
            profile["type"] = "numeric"
            mean = df[col].mean()
            profile["statistics"] = {
                "mean": None if pd.isna(mean) else round(float(mean), 2),
                "median": round(float(df[col].median()), 2),
                "std": round(float(df[col].std()), 2),
                "min": round(float(df[col].min()), 2),
                "max": round(float(df[col].max()), 2),
                "q1": round(float(df[col].quantile(0.25)), 2),
                "q3": round(float(df[col].quantile(0.75)), 2),
            }
        elif pd.api.types.is_bool_dtype(df[col]):
            profile["type"] = "boolean"
        elif pd.api.types.is_datetime64_any_dtype(df[col]):
            profile["type"] = "datetime"
        else:
            profile["type"] = "categorical"

        counts = df[col].value_counts()
        if not counts.empty:
            tv = counts.index[0]
            profile["distribution"] = {
                "top_value": tv.item() if hasattr(tv, "item") else str(tv),
                "top_count": int(counts.iloc[0]),
            }

        profiles.append(profile)

    return profiles
