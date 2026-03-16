import asyncio
import os
from supabase import acreate_client, AsyncClient

SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("SUPABASE_URL and SUPABASE_KEY must be set in environment")

_client: AsyncClient | None = None
_client_lock = asyncio.Lock()

async def get_supabase_client() -> AsyncClient:
    global _client
    if _client is not None:
        return _client
    async with _client_lock:
        if _client is None:
            _client = await acreate_client(SUPABASE_URL, SUPABASE_KEY)
    return _client
