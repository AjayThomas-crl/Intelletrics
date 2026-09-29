import math

import pandas as pd
import pytest

from query_engine import execute_sql
from query_runner import execute_in_isolated_process


@pytest.fixture
def frame():
    return pd.DataFrame({
        "Region": ["East", "West", "East", "West", None],
        "Revenue": [100, 200, 300, 400, None],
        "Cost": [50, 100, 150, 200, None],
        "Date": ["2026-01-01", "2026-01-02", "2026-02-01", "2026-02-02", None],
    })


def test_filtered_aggregate(frame):
    result = execute_sql(frame, "SELECT SUM(c1) AS revenue FROM data WHERE c0 = 'East'")
    assert result.rows == [{"revenue": 400}]
    assert result.source_columns == ["Region", "Revenue"]


def test_groups_order_and_percentages(frame):
    result = execute_sql(frame, "SELECT c0, sum(c1) AS sales, 100.0*sum(c1)/(SELECT sum(c1) FROM data) AS share FROM data WHERE c0 IS NOT NULL GROUP BY c0 ORDER BY sales DESC")
    assert result.rows == [{"Region": "West", "sales": 600, "share": 60}, {"Region": "East", "sales": 400, "share": 40}]


def test_cte_date_trend_and_window(frame):
    result = execute_sql(frame, "WITH monthly AS (SELECT strftime('%Y-%m', c3) AS month, sum(c1) AS sales FROM data WHERE c3 IS NOT NULL GROUP BY month) SELECT month, sales, sales-lag(sales) OVER (ORDER BY month) AS growth FROM monthly ORDER BY month")
    assert result.rows == [{"month": "2026-01", "sales": 300, "growth": None}, {"month": "2026-02", "sales": 700, "growth": 400}]


def test_statistics(frame):
    result = execute_sql(frame, "SELECT median(c1) AS median, stddev(c1) AS sd, variance(c1) AS variance, corr(c1,c2) AS correlation FROM data").rows[0]
    assert result["median"] == 250
    assert result["sd"] == pytest.approx(math.sqrt(50000 / 3))
    assert result["variance"] == pytest.approx(50000 / 3)
    assert result["correlation"] == pytest.approx(1)


def test_null_and_empty_aggregates(frame):
    assert execute_sql(frame, "SELECT count(*) AS missing FROM data WHERE c1 IS NULL").rows == [{"missing": 1}]
    assert execute_sql(frame, "SELECT sum(c1) AS total FROM data WHERE c1 > 1000").rows == [{"total": None}]
    assert execute_sql(frame, "SELECT c0 FROM data WHERE c1 > 1000").rows == []


def test_arbitrary_headers_and_values():
    frame = pd.DataFrame({"count": ["O'Reilly"], "A": [3], "a": [4], 'a"; DROP TABLE data;--': [5]})
    result = execute_sql(frame, "SELECT c0, c1+c2+c3 AS total FROM data WHERE c0 = 'O''Reilly'")
    assert result.rows == [{"count": "O'Reilly", "total": 12}]
    assert result.source_columns == list(frame.columns)


@pytest.mark.parametrize("sql", [
    "DROP TABLE data", "DELETE FROM data", "UPDATE data SET c1=0",
    "INSERT INTO data(c1) VALUES(1)", "CREATE TABLE evil(x)",
    "ATTACH DATABASE '/tmp/evil.db' AS evil", "PRAGMA table_info(data)",
    "SELECT * FROM sqlite_master", "SELECT load_extension('/tmp/evil') FROM data",
    "SELECT readfile('/etc/passwd') FROM data", "SELECT randomblob(1000000000) FROM data",
    "SELECT * FROM data; DROP TABLE data", "SELECT * FROM another_dataset",
    "WITH RECURSIVE x(n) AS (VALUES(1) UNION ALL SELECT n+1 FROM x) SELECT * FROM x, data",
    "SELECT 42 AS invented", "SELECT c999 FROM data",
])
def test_rejects_unsafe_or_invalid_queries(frame, sql):
    with pytest.raises(ValueError):
        execute_sql(frame, sql)
    assert frame["Revenue"].iloc[0] == 100


def test_unknown_quoted_column_rejected(frame):
    import sqlite3
    if not hasattr(sqlite3.Connection, "setconfig"):
        pytest.skip("DQS configuration requires Python 3.12+")
    with pytest.raises(ValueError):
        execute_sql(frame, 'SELECT "c999" FROM data')


def test_duplicate_output_names_rejected(frame):
    with pytest.raises(ValueError, match="unique alias"):
        execute_sql(frame, "SELECT c1 AS same, c2 AS same FROM data")


def test_result_limit_does_not_truncate_aggregates():
    frame = pd.DataFrame({"n": range(150)})
    result = execute_sql(frame, "SELECT * FROM data ORDER BY c0")
    assert len(result.rows) == 100 and result.truncated
    total = execute_sql(frame, "SELECT sum(c0) AS total FROM data")
    assert total.rows == [{"total": sum(range(150))}] and not total.truncated


def test_execution_timeout():
    frame = pd.DataFrame({"n": range(100)})
    with pytest.raises(TimeoutError):
        execute_sql(frame, "SELECT sum(a.c0*b.c0*c.c0) FROM data a, data b, data c", timeout=0)


def test_spawned_worker_success_and_failure(frame):
    assert execute_in_isolated_process(frame, "SELECT count(*) AS n FROM data").rows == [{"n": 5}]
    with pytest.raises(ValueError):
        execute_in_isolated_process(frame, "DROP TABLE data")


def test_spawned_worker_timeout(frame, monkeypatch):
    import query_runner
    monkeypatch.setattr(query_runner, "QUERY_TIMEOUT_SECONDS", 0)
    with pytest.raises(TimeoutError):
        execute_in_isolated_process(frame, "SELECT count(*) FROM data")
