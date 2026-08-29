"""
VeriGate Backend — Supabase Database Client

Provides a configured Supabase client for database operations.
Uses the anon key with permissive RLS policies for the hackathon MVP.
"""

from functools import lru_cache

from supabase import create_client, Client

from app.core.config import get_settings


@lru_cache
def get_supabase_client() -> Client:
    """Return a cached Supabase client using the anon key."""
    settings = get_settings()
    # Use anon key for the MVP since permissive RLS policies are in place
    api_key = settings.supabase_anon_key
    return create_client(
        supabase_url=settings.supabase_url,
        supabase_key=api_key,
    )


def get_db() -> Client:
    """FastAPI dependency that provides the Supabase client."""
    return get_supabase_client()
