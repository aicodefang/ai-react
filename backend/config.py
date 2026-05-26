from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
CUSTOMERS_FILE = BASE_DIR / "customers.json"


def load_env_file() -> None:
    env_path = BASE_DIR / ".env"
    if not env_path.exists():
        return

    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


@dataclass(frozen=True)
class Settings:
    supabase_url: str
    supabase_key: str
    supabase_pages_table: str
    supabase_apis_table: str
    supabase_bindings_table: str
    xiaomi_api_base: str
    xiaomi_api_key: str
    xiaomi_model: str
    customers_file: Path


def get_settings() -> Settings:
    load_env_file()
    return Settings(
        supabase_url=os.getenv("SUPABASE_URL", "").rstrip("/"),
        supabase_key=os.getenv("SUPABASE_KEY", ""),
        supabase_pages_table=os.getenv("SUPABASE_PAGES_TABLE") or os.getenv("SUPABASE_TABLE", "pages"),
        supabase_apis_table=os.getenv("SUPABASE_APIS_TABLE", "api_definitions"),
        supabase_bindings_table=os.getenv("SUPABASE_BINDINGS_TABLE", "page_api_bindings"),
        xiaomi_api_base=os.getenv("XIAOMI_API_BASE", "https://token-plan-sgp.xiaomimimo.com/v1").rstrip("/"),
        xiaomi_api_key=os.getenv("XIAOMI_API_KEY", ""),
        xiaomi_model=os.getenv("XIAOMI_MODEL", "mimo-v2.5-pro"),
        customers_file=CUSTOMERS_FILE,
    )
