"""agregar estado pending a memberships

Revision ID: bcaa5ca1808f
Revises: d886a6501c9d
Create Date: 2026-08-13 21:32:14.358305

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bcaa5ca1808f'
down_revision: Union[str, None] = 'd886a6501c9d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE membershipstatus ADD VALUE IF NOT EXISTS 'pending'")


def downgrade() -> None:
    # Postgres no permite sacar un valor de un enum fácilmente; si necesitás
    # revertir esto en algún momento, hay que recrear el tipo desde cero.
    pass