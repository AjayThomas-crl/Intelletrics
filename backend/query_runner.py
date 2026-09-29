"""Run read-only dataset queries in a short-lived, resource-limited process."""
from __future__ import annotations

import multiprocessing as mp
from typing import Any

# Includes interpreter startup and copying/loading the dataset, not just SQL time.
QUERY_TIMEOUT_SECONDS = 20


def _worker(connection, dataframe: Any, sql: str) -> None:
    try:
        try:
            import resource
            resource.setrlimit(resource.RLIMIT_CPU, (QUERY_TIMEOUT_SECONDS, QUERY_TIMEOUT_SECONDS))
        except (ImportError, OSError, ValueError):
            pass
        from query_engine import execute_sql
        connection.send((True, execute_sql(dataframe, sql)))
    except Exception as exc:
        connection.send((False, (type(exc).__name__, str(exc))))
    finally:
        connection.close()


def execute_in_isolated_process(dataframe: Any, sql: str):
    context = mp.get_context("spawn")
    parent, child = context.Pipe(duplex=False)
    process = context.Process(target=_worker, args=(child, dataframe, sql), daemon=True)
    started = False
    try:
        process.start()
        started = True
        child.close()
        if not parent.poll(QUERY_TIMEOUT_SECONDS):
            raise TimeoutError("The data operation exceeded the time limit")
        try:
            success, payload = parent.recv()
        except EOFError as exc:
            raise RuntimeError("The isolated query worker exited unexpectedly") from exc
        if not success:
            error_type, message = payload
            if error_type == "ValueError":
                raise ValueError(message)
            if error_type == "TimeoutError":
                raise TimeoutError(message)
            raise RuntimeError(message)
        return payload
    finally:
        child.close()
        parent.close()
        if started:
            process.join(timeout=0.1)
            if process.is_alive():
                process.terminate()
                process.join(timeout=1)
            if process.is_alive():
                process.kill()
                process.join()
            process.close()
