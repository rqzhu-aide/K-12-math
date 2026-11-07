"""Locate the published database while accepting standalone older bank snapshots."""
from pathlib import Path


def database_root(root):
    root = Path(root)
    database = root / 'database'
    return database if database.is_dir() else root
