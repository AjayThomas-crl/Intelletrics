from __future__ import annotations

from typing import Any

from supabase import Client

from config import SUPABASE_STORAGE_BUCKET


def storage_path(user_id: str, dataset_id: str, filename: str) -> str:
    # The user id is the first path segment, making ownership auditable in Storage.
    safe_name = filename.replace("/", "_").replace("\\", "_")
    return f"{user_id}/{dataset_id}/{safe_name}"


def save_dataset(
    client: Client,
    *,
    dataset_id: str,
    user_id: str,
    filename: str,
    content: bytes,
    content_type: str,
    rows: int,
    columns: int,
    column_names: list[str],
    preview: list[dict[str, Any]],
    profiles: list[dict[str, Any]],
) -> None:
    path = storage_path(user_id, dataset_id, filename)
    client.storage.from_(SUPABASE_STORAGE_BUCKET).upload(
        path,
        content,
        {"content-type": content_type or "application/octet-stream", "upsert": False},
    )
    client.table("datasets").insert(
        {
            "id": dataset_id,
            "user_id": user_id,
            "filename": filename,
            "storage_path": path,
            "content_type": content_type,
            "row_count": rows,
            "column_count": columns,
            "column_names": column_names,
            "preview": preview,
            "profile": profiles,
            "status": "ready",
        }
    ).execute()


def get_dataset(client: Client, dataset_id: str, user_id: str) -> dict[str, Any] | None:
    result = (
        client.table("datasets")
        .select("*")
        .eq("id", dataset_id)
        .eq("user_id", user_id)
        .maybe_single()
        .execute()
    )
    return result.data


def download_dataset(client: Client, dataset: dict[str, Any]) -> bytes:
    return client.storage.from_(SUPABASE_STORAGE_BUCKET).download(dataset["storage_path"])
