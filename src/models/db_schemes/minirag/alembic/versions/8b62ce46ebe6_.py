"""empty message

Revision ID: 8b62ce46ebe6
Revises: 1ba5a74b2025, b2e865166241
Create Date: 2025-06-25 13:28:35.251298

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8b62ce46ebe6'
down_revision: Union[str, None] = ('1ba5a74b2025', 'b2e865166241')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass
    


def downgrade() -> None:
    pass
