"""Execute model-generated SQL against an ephemeral, read-only dataset database.

No eval/exec, file-backed databases, extensions, or user-supplied Python. SQLite's
runtime authorizer enforces access; prompt instructions are not a security boundary.
"""
from __future__ import annotations

import math
import json
import sqlite3
import statistics
import time
from contextlib import closing
from dataclasses import dataclass
from typing import Any

import pandas as pd

MAX_RESULT_ROWS = 100
MAX_SQL_LENGTH = 6000
MAX_RESULT_BYTES = 256 * 1024
QUERY_SECONDS = 5
SAFE_FUNCTIONS = frozenset("""
abs avg coalesce count ifnull nullif round sum total min max
lower upper trim ltrim rtrim length substr substring replace instr like glob
 date datetime time strftime julianday unixepoch
row_number rank dense_rank percent_rank cume_dist ntile lag lead
first_value last_value nth_value
median stddev variance corr sqrt power
""".split())


@dataclass
class QueryResult:
    rows: list[dict[str, Any]]
    source_columns: list[str]
    truncated: bool = False


def safe_value(value: Any) -> Any:
    if value is None or pd.isna(value):
        return None
    if hasattr(value, "item"):
        return safe_value(value.item())
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


class Median:
    def __init__(self):
        self.values = []

    def step(self, value):
        if value is not None:
            self.values.append(float(value))

    def finalize(self):
        return statistics.median(self.values) if self.values else None


class Variance:
    def __init__(self):
        self.n, self.mean, self.m2 = 0, 0.0, 0.0

    def step(self, value):
        if value is not None:
            self.n += 1
            delta = float(value) - self.mean
            self.mean += delta / self.n
            self.m2 += delta * (float(value) - self.mean)

    def finalize(self):
        return max(0.0, self.m2 / (self.n - 1)) if self.n > 1 else None


class Stddev(Variance):
    def finalize(self):
        variance = super().finalize()
        return math.sqrt(variance) if variance is not None else None


class Correlation:
    def __init__(self):
        self.n = 0
        self.x = self.y = self.xx = self.yy = self.xy = 0.0

    def step(self, x, y):
        if x is None or y is None:
            return
        x, y = float(x), float(y)
        self.n += 1
        dx, dy = x - self.x, y - self.y
        self.x += dx / self.n
        self.y += dy / self.n
        self.xx += dx * (x - self.x)
        self.yy += dy * (y - self.y)
        self.xy += dx * (y - self.y)

    def finalize(self):
        if self.n < 2 or self.xx <= 0 or self.yy <= 0:
            return None
        return max(-1.0, min(1.0, self.xy / math.sqrt(self.xx * self.yy)))


def execute_sql(frame: pd.DataFrame, sql: str, *, timeout: float = QUERY_SECONDS) -> QueryResult:
    if not sql.strip() or len(sql) > MAX_SQL_LENGTH:
        raise ValueError("Query is empty or too long")
    columns = {f"c{i}": str(name) for i, name in enumerate(frame.columns)}
    # Internal IDs support arbitrary, case-sensitive, or SQL-reserved CSV headers.
    table = frame.copy(deep=False)
    table.columns = list(columns)
    sources: set[str] = set()
    read_dataset = False

    def authorize(action, arg1, arg2, database, trigger):
        nonlocal read_dataset
        if action == sqlite3.SQLITE_SELECT:
            return sqlite3.SQLITE_OK
        if action == sqlite3.SQLITE_READ and database in ("main", None) and arg1 == "data":
            read_dataset = True
            if arg2 in columns:
                sources.add(arg2)
            return sqlite3.SQLITE_OK
        if action == sqlite3.SQLITE_FUNCTION and (arg2 or "").lower() in SAFE_FUNCTIONS:
            return sqlite3.SQLITE_OK
        return sqlite3.SQLITE_DENY

    with closing(sqlite3.connect(":memory:")) as connection:
        connection.execute("PRAGMA temp_store=MEMORY")
        connection.execute("PRAGMA trusted_schema=OFF")
        # Disable SQLite's legacy interpretation of unknown quoted columns as strings.
        if hasattr(connection, "setconfig"):
            connection.setconfig(sqlite3.SQLITE_DBCONFIG_DQS_DML, False)
        table.to_sql("data", connection, index=False, chunksize=1000)
        connection.create_aggregate("median", 1, Median)
        connection.create_aggregate("variance", 1, Variance)
        connection.create_aggregate("stddev", 1, Stddev)
        connection.create_aggregate("corr", 2, Correlation)
        connection.create_function("sqrt", 1, lambda x: math.sqrt(x) if x is not None and x >= 0 else None)
        connection.create_function("power", 2, lambda x, y: math.pow(x, y) if x is not None and y is not None else None)
        connection.execute("PRAGMA query_only=ON")
        connection.setlimit(sqlite3.SQLITE_LIMIT_SQL_LENGTH, MAX_SQL_LENGTH)
        connection.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, 1_000_000)
        connection.setlimit(sqlite3.SQLITE_LIMIT_COLUMN, 256)
        connection.setlimit(sqlite3.SQLITE_LIMIT_EXPR_DEPTH, 50)
        connection.setlimit(sqlite3.SQLITE_LIMIT_COMPOUND_SELECT, 10)
        connection.setlimit(sqlite3.SQLITE_LIMIT_ATTACHED, 0)
        connection.set_authorizer(authorize)
        deadline = time.monotonic() + timeout
        connection.set_progress_handler(lambda: int(time.monotonic() >= deadline), 1000)
        try:
            cursor = connection.execute(sql)
            if cursor.description is None or not read_dataset:
                raise ValueError("Query must read the uploaded dataset")
            labels = [columns.get(item[0].lower(), item[0]) for item in cursor.description]
            if len(set(labels)) != len(labels):
                raise ValueError("Use a unique alias for each result column")
            records = []
            result_bytes = 0
            truncated = False
            for row in cursor:
                if len(records) == MAX_RESULT_ROWS:
                    truncated = True
                    break
                record = {label: safe_value(value) for label, value in zip(labels, row)}
                result_bytes += len(json.dumps(record, ensure_ascii=False).encode("utf-8"))
                if result_bytes > MAX_RESULT_BYTES:
                    if not records:
                        raise ValueError("Result row is too large; select fewer columns or shorter text")
                    truncated = True
                    break
                records.append(record)
        except sqlite3.Error as exc:
            if "interrupted" in str(exc):
                raise TimeoutError("The data operation exceeded the time limit") from exc
            raise ValueError(f"Invalid dataset query: {exc}") from exc
    return QueryResult(
        rows=records,
        source_columns=[name for key, name in columns.items() if key in sources],
        truncated=truncated,
    )
