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