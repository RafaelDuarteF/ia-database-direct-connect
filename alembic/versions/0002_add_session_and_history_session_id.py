"""
add session table and session_id to history
"""
revision = '0002_session_and_history'
down_revision = '0001_create_history_table'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa

def upgrade():
    op.create_table(
        'session',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.add_column('history', sa.Column('session_id', sa.Integer(), sa.ForeignKey('session.id'), nullable=False, server_default='1'))
    # Opcional: migrar dados existentes para session_id=1
    # Cria uma sessão default se necessário
    conn = op.get_bind()
    conn.execute(sa.text("INSERT INTO session (id, created_at) VALUES (1, NOW()) ON DUPLICATE KEY UPDATE id=id"))
    conn.execute(sa.text("UPDATE history SET session_id=1 WHERE session_id IS NULL"))
    op.alter_column('history', 'session_id', server_default=None)

def downgrade():
    op.drop_constraint('history_ibfk_1', 'history', type_='foreignkey')
    op.drop_column('history', 'session_id')
    op.drop_table('session')
