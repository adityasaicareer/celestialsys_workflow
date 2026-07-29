"""Initial unified visitor-management schema migration."""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create all application tables from the ORM metadata."""
    from database import Base
    import models.entities  # noqa: F401
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    """Drop all application tables."""
    from database import Base
    import models.entities  # noqa: F401
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
