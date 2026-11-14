"""initial_schema

Revision ID: 1417480b8e5d
Revises: 
Create Date: 2026-11-14 11:42:58.981178

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1417480b8e5d'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Hospitals table
    op.create_table(
        'hospitals',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('location', sa.String(length=150), nullable=False),
        sa.Column('contact', sa.String(length=50), nullable=False),
        sa.Column('is_sample', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_hospitals_id'), 'hospitals', ['id'], unique=False)
    op.create_index(op.f('ix_hospitals_name'), 'hospitals', ['name'], unique=False)

    # 2. Resources table
    op.create_table(
        'resources',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('hospital_id', sa.Integer(), nullable=True),
        sa.Column('resource_type', sa.String(length=50), nullable=False),
        sa.Column('total', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('available', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('occupied', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='Available'),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['hospital_id'], ['hospitals.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_resources_id'), 'resources', ['id'], unique=False)
    op.create_index(op.f('ix_resources_resource_type'), 'resources', ['resource_type'], unique=False)

    # 3. Emergencies table
    op.create_table(
        'emergencies',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('case_id', sa.String(length=20), nullable=False),
        sa.Column('emergency_type', sa.String(length=100), nullable=False),
        sa.Column('location', sa.String(length=150), nullable=False),
        sa.Column('hospital_name', sa.String(length=150), nullable=False),
        sa.Column('priority', sa.String(length=20), nullable=False),
        sa.Column('status', sa.String(length=30), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_emergencies_id'), 'emergencies', ['id'], unique=False)
    op.create_index(op.f('ix_emergencies_case_id'), 'emergencies', ['case_id'], unique=True)

    # 4. Report Audits table
    op.create_table(
        'report_audits',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('file_size_kb', sa.Float(), nullable=False),
        sa.Column('content_type', sa.String(length=100), nullable=False),
        sa.Column('processing_status', sa.String(length=50), nullable=False),
        sa.Column('temporary_file_cleaned', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('processed_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_report_audits_id'), 'report_audits', ['id'], unique=False)


def downgrade() -> None:
    op.drop_table('report_audits')
    op.drop_table('emergencies')
    op.drop_table('resources')
    op.drop_table('hospitals')
