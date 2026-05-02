from pathlib import Path
import os
import sys

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_ANON_KEY", "test-anon-key")
os.environ.setdefault("LITELLM_PROXY_URL", "https://example.litellm.ai")
os.environ.setdefault("LITELLM_VIRTUAL_KEY", "test-llm-key")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/db")

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
