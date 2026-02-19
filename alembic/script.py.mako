# mako template for Alembic migration scripts
"""
Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}
"""
revision = "${up_revision}"
down_revision = ${repr(down_revision) if down_revision else None}
branch_labels = ${repr(branch_labels) if branch_labels else None}
depends_on = ${repr(depends_on) if depends_on else None}

from alembic import op
import sqlalchemy as sa
% if imports:
${imports}
% endif

def upgrade():
% if upgrades:
${upgrades}
% else:
    pass
% endif

def downgrade():
% if downgrades:
${downgrades}
% else:
    pass
% endif
