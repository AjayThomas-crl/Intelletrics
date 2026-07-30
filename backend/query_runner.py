"""Run the allowlisted Pandas query in a separate short-lived process."""

from __future__ import annotations

import multiprocessing as mp
from typing import Any


QUERY_TIMEOUT_SECONDS = 5


def _worker(connection, dataframe: Any, plan: Any) -> None:
    try:
        # This is a resource limit, not a security boundary. The worker still
        # runs inside the backend container and receives no arbitrary code.
        try:
            import resource

            resource.setrlimit(resource.RLIMIT_CPU, (QUERY_TIMEOUT_SECONDS, QUERY_TIMEOUT_SECONDS))
        except (ImportError, OSError, ValueError):
            pass

        # Import lazily so spawning this worker does not create an import cycle.
        from ask_on_data import execute_query_plan

        connection.send((True, execute_query_plan(dataframe, plan)))
    except Exception as exc:
        connection.send((False, (type(exc).__name__, str(exc))))
    finally:
        connection.close()


def execute_in_isolated_process(dataframe: Any, plan: Any):
    """Execute one query in a spawned worker and terminate it on timeout."""
    context = mp.get_context("spawn")
    parent, child = context.Pipe(duplex=False)
    process = context.Process(target=_worker, args=(child, dataframe, plan))
    process.start()
    child.close()

    try:
        if not parent.poll(QUERY_TIMEOUT_SECONDS):
            process.terminate()
            process.join(timeout=1)
            raise TimeoutError("The data operation exceeded the time limit")

        try:
            success, payload = parent.recv()
        except EOFError as exc:
            raise RuntimeError("The isolated query worker exited unexpectedly") from exc
        if not success:
            error_type, message = payload
            if error_type == "ValueError":
                raise ValueError(message)
            raise RuntimeError(message)
        return payload
    finally:
        if process.is_alive():
            process.terminate()
        process.join(timeout=1)
        parent.close()
