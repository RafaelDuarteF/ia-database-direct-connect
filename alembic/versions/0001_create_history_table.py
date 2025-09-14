"""
create history table
"""
revision = '0001_create_history_table'
down_revision = None
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa

def upgrade():
    op.create_table(
        'history',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('question', sa.Text(), nullable=False),
        sa.Column('answer', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )

def downgrade():
    op.drop_table('history')
