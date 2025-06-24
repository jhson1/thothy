from contextlib import contextmanager
import os
from sqlalchemy import create_engine
from sqlmodel import Session


# Use Supabase PostgreSQL database URL
# Format: postgresql://[user[:password]@][netloc][:port][/dbname][?param1=value1&...]
def get_database_url():
    """Get the database URL from Supabase environment variables."""

    # Use Supabase-specific environment variables
    supabase_url = os.getenv("SUPABASE_DATABASE_URL")
    if supabase_url:
        if supabase_url.startswith("postgres://"):
            supabase_url = supabase_url.replace(
                "postgres://", "postgresql://", 1)
        # Do NOT add options or schema_param here
        return supabase_url

    # Fallback error
    raise ValueError(
        "Database configuration not found. Please set one of:\n"
        "- DATABASE_URL\n"
        "- SUPABASE_DATABASE_URL\n"
        "- SUPABASE_HOST, SUPABASE_DB_NAME, SUPABASE_USER, SUPABASE_PASSWORD"
    )


sql_url = get_database_url()

# PostgreSQL engine configuration
sql_engine = create_engine(
    sql_url,
    # PostgreSQL-specific configuration
    pool_size=10,                    # Number of connections to maintain
    max_overflow=20,                 # Additional connections beyond pool_size
    pool_timeout=30,                 # Timeout for getting connection from pool
    pool_recycle=3600,              # Recycle connections after 1 hour
    pool_pre_ping=True,             # Validate connections before use
    echo=False,                     # Set to True for SQL query logging
)


@contextmanager
def get_sql_session():
    """Get a database session with proper cleanup."""
    session = Session(sql_engine)
    try:
        yield session
    finally:
        session.close()
