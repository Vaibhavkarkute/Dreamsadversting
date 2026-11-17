"""Initial normalized 34-table PostgreSQL schema for DreamsAdverstings OOH/DOOH Marketplace.

Revision ID: 001_initial_schema
Revises: None
Create Date: 2026-11-16
"""
from alembic import op
import sqlalchemy as sa

revision = "001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    from app.models.entities import Base
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    from app.models.entities import Base
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
