"""empty message

Revision ID: 1c90e0fd276a
Revises: a6f7dd522b7
Create Date: 2014-06-24 19:01:39.358682

"""

# revision identifiers, used by Alembic.
revision = '1c90e0fd276a'
down_revision = 'a6f7dd522b7'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('user', sa.Column('winrate_data', sa.Json(), nullable=True))
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('user', 'winrate_data')
    ### end Alembic commands ###
