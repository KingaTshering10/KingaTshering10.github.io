"""`python -m app.seed` — creates any missing tables, then loads demo data."""

import app.models  # noqa: F401 — register tables on Base.metadata
from app.db.base import Base
from app.db.session import get_engine
from app.seed.seed import main

Base.metadata.create_all(get_engine())
main()
