import numpy as np
import re

def generate_charts(df, profiles):
    keywords = [
        "id",
        "employeeid", "customerid", "userid", "orderid", "invoiceid",
        "uuid", "serial", "employee",
    ]
    # whole-word match: "id" matches "id" or "order_id" but not "provided"
    kw_patterns = [re.compile(r"\b" + re.escape(kw) + r"\b", re.IGNORECASE) for kw in keywords]

    charts = []
    for profile in profiles:
        c = {}
        col = profile["name"]
        c["column"] = col

        if any(p.search(col) for p in kw_patterns):
            continue

        if profile["type"]==("numeric"):
            
            c["chart"]="histogram"
            # bins for histogram

            values=df[col].dropna()
            hist_count,bins=np.histogram(values,bins=10)
            labels=[]
            for i in range (len(hist_count)):
                labels.append(f"{bins[i]:.0f}-{bins[i+1]:.0f}")

            
            c["labels"]=labels
            c["values"]=[int(v) for v in hist_count.tolist()]

        else:

            if profile["uniqueness"]["ratio"] > 20:
                continue

            c["chart"]="bar"
            counts=df[col].value_counts()
            c["labels"]=[str(k) for k in counts.index.tolist()]
            c["values"]=[int(v) for v in counts.values.tolist()]

        
        charts.append(c)
    
    return charts

def charts_description(charts: list[dict], profiles: list[dict]) -> list[dict]:
    """Attach a one-line heuristic description to each chart.

    No AI — uses the profiler stats directly.  Mutates and returns *charts*
    with an added ``description`` field.
    """
    profile_map = {p["name"]: p for p in profiles}

    for c in charts:
        col = c["column"]
        p = profile_map.get(col, {})
        ptype = p.get("type", "")
        missing = p.get("missing", {}).get("count", 0)
        missing_pct = p.get("missing", {}).get("percentage", 0.0)

        if ptype == "numeric":
            stats = p.get("statistics", {})
            parts = [
                f"Range {stats.get('min','?')}–{stats.get('max','?')}",
                f"median {stats.get('median','?')}",
            ]
            if missing:
                parts.append(f"{missing} missing ({missing_pct}%)")
            c["description"] = f"Histogram of {col} — {', '.join(parts)}"
        else:
            dist = p.get("distribution", {})
            parts = [f"Top: \"{dist.get('top_value','?')}\" ({dist.get('top_count','?')} rows)"]
            if missing:
                parts.append(f"{missing} missing ({missing_pct}%)")
            c["description"] = f"Bar chart of {col} — {', '.join(parts)}"

    return charts