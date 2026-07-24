import os
from pathlib import Path


def _load_local_env() -> None:
    """Load backend/.env without adding a dotenv runtime dependency."""
    env_path = Path(__file__).resolve().parent / ".env"
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        name = name.strip()
        value = value.strip().strip('"').strip("'")
        # Explicit process environment variables always win over .env values.
        os.environ.setdefault(name, value)


_load_local_env()

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
_legacy_supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
SUPABASE_PUBLISHABLE_KEY = os.getenv(
    "SUPABASE_PUBLISHABLE_KEY",
    os.getenv("NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY", "")
    or (_legacy_supabase_key if _legacy_supabase_key.startswith("sb_publishable_") else ""),
)
SUPABASE_STORAGE_BUCKET = os.getenv("SUPABASE_STORAGE_BUCKET", "datasets")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", str(25 * 1024 * 1024)))
MAX_ROWS = int(os.getenv("MAX_ROWS", "250000"))
MAX_COLUMNS = int(os.getenv("MAX_COLUMNS", "200"))


def require_supabase_config() -> None:
    if not SUPABASE_URL or not SUPABASE_PUBLISHABLE_KEY:
        raise RuntimeError(
            "SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY must be configured in backend/.env"
        )
