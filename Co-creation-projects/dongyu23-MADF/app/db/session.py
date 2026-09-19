from app.db.client import get_db, db_manager

# Backward compatibility for existing code that might import engine/SessionLocal
# We are removing SQLAlchemy, so these are just placeholders or removed.
# But since we are rewriting the entire DB layer, we don't need to keep them if we fix all usages.
# For now, let's just export get_db which is the main dependency.

__all__ = ["get_db", "db_manager"]
