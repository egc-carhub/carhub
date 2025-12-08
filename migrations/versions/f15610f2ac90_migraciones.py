"""migraciones

Revision ID: f15610f2ac90
Revises: 
Create Date: 2025-12-08 21:40:38.072424

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f15610f2ac90'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # 1. Crear TABLAS NUEVAS (que no estaban en 001)
    # ------------------------------------------------
    op.create_table('community',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=50), nullable=False),
    sa.Column('description', sa.String(length=255), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name')
    )
    
    op.create_table('deposition',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('dep_metadata', sa.JSON(), nullable=False),
    sa.Column('status', sa.String(length=50), nullable=False),
    sa.Column('doi', sa.String(length=250), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('doi')
    )

    op.create_table('user_sessions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('session_token', sa.String(length=512), nullable=False),
    sa.Column('ip_address', sa.String(length=64), nullable=True),
    sa.Column('user_agent', sa.String(length=512), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('last_activity', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('session_token')
    )

    op.create_table('community_members',
    sa.Column('community_id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['community_id'], ['community.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('community_id', 'user_id')
    )

    # 2. Modificar TABLAS EXISTENTES (User)
    # ------------------------------------------------
    # Agregamos las columnas de 2FA que faltaban en la 001
    op.add_column('user', sa.Column('two_factor_enabled', sa.Boolean(), nullable=True))
    op.add_column('user', sa.Column('two_factor_secret', sa.String(length=32), nullable=True))


def downgrade():
    # Orden inverso
    op.drop_column('user', 'two_factor_secret')
    op.drop_column('user', 'two_factor_enabled')
    op.drop_table('community_members')
    op.drop_table('user_sessions')
    op.drop_table('deposition')
    op.drop_table('community')