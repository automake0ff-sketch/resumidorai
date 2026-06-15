import os
from supabase import create_client, Client

_supabase: Client | None = None


async def init_supabase():
    global _supabase
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_SERVICE_KEY"]
    _supabase = create_client(url, key)


def get_db() -> Client:
    if _supabase is None:
        raise RuntimeError("Supabase not initialized")
    return _supabase
