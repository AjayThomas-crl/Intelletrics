"""One parser for uploaded files and files restored from persistent storage."""
from io import BytesIO

import pandas as pd
from fastapi import HTTPException

from config import MAX_COLUMNS, MAX_ROWS, MAX_UPLOAD_BYTES


def parse_dataset(filename: str, content: bytes) -> pd.DataFrame:
    if not content:
        raise HTTPException(400, "The uploaded file is empty")
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "Dataset exceeds the upload size limit")
    suffix = filename.lower().rsplit(".", 1)[-1]
    try:
        if suffix == "csv":
            frame = pd.read_csv(BytesIO(content))
        elif suffix in {"xlsx", "xls"}:
            frame = pd.read_excel(BytesIO(content))
        else:
            raise HTTPException(415, "Only .csv, .xlsx, and .xls files are supported")
    except (UnicodeDecodeError, ValueError, OSError, ImportError) as exc:
        raise HTTPException(400, "Could not parse dataset") from exc
    rows, columns = frame.shape
    if rows == 0 or columns == 0:
        raise HTTPException(400, "The dataset must contain at least one row and one column")
    if rows > MAX_ROWS or columns > MAX_COLUMNS:
        raise HTTPException(413, f"Dataset exceeds the {MAX_ROWS:,} row or {MAX_COLUMNS} column limit")
    frame.columns = [str(column).strip() or f"column_{i + 1}" for i, column in enumerate(frame.columns)]
    if frame.columns.duplicated().any():
        raise HTTPException(400, "Column names must be unique")
    return frame
