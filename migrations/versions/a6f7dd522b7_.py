"""empty message

Revision ID: a6f7dd522b7
Revises: None
Create Date: 2014-06-22 22:35:25.691983

"""

# revision identifiers, used by Alembic.
revision = 'a6f7dd522b7'
down_revision = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.create_table('user',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('steam_id', sa.String(length=40), nullable=True),
    sa.Column('forum_id', sa.Integer(), nullable=True),
    sa.Column('teamspeak_id', sa.String(length=200), nullable=True),
    sa.Column('nickname', sa.String(length=80), nullable=True),
    sa.Column('avatar', sa.String(length=255), nullable=True),
    sa.Column('admin', sa.Boolean(), nullable=True),
    sa.Column('bio_text', sa.String(length=4096), nullable=True),
    sa.Column('created', sa.DateTime(), nullable=True),
    sa.Column('last_seen', sa.DateTime(), nullable=True),
    sa.Column('twitch', sa.String(length=60), nullable=True),
    sa.Column('random_heroes', sa.Json(), nullable=True),
    sa.Column('az_completions', sa.Integer(), nullable=True),
    sa.Column('public', sa.Boolean(), nullable=True),
    sa.Column('logo', sa.Boolean(), nullable=True),
    sa.Column('points_from_events', sa.Integer(), nullable=True),
    sa.Column('points_from_ts3', sa.Integer(), nullable=True),
    sa.Column('points_from_forum', sa.Integer(), nullable=True),
    sa.Column('ts3_starttime', sa.DateTime(), nullable=True),
    sa.Column('ts3_endtime', sa.DateTime(), nullable=True),
    sa.Column('ts3_rewardtime', sa.DateTime(), nullable=True),
    sa.Column('ts3_connections', sa.Json(), nullable=True),
    sa.Column('last_post_reward', sa.Integer(), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('steam_id'),
    sa.UniqueConstraint('teamspeak_id')
    )
    op.create_table('teamspeak_data',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('time', sa.DateTime(), nullable=True),
    sa.Column('clients', sa.Json(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('event',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=200), nullable=True),
    sa.Column('desc', sa.String(length=4096), nullable=True),
    sa.Column('type', sa.String(length=20), nullable=True),
    sa.Column('start_time', sa.DateTime(), nullable=True),
    sa.Column('end_time', sa.DateTime(), nullable=True),
    sa.Column('points', sa.Integer(), nullable=True),
    sa.Column('reward_threshold', sa.Integer(), nullable=True),
    sa.Column('total_subchans', sa.Integer(), nullable=True),
    sa.Column('channels', sa.Json(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('event')
    op.drop_table('teamspeak_data')
    op.drop_table('user')
    ### end Alembic commands ###