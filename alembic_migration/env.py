from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy_utils import URLType
from sqlalchemy.orm import relationship
Base = declarative_base()


class Server(Base):
    __tablename__ = "server"
    id = Column(Integer, primary_key=True)
    server_id = Column(String)
    server_name = Column(String)
    admin_id = Column(String)
    admin_name = Column(String)
    twitter_account_id = Column(Integer, ForeignKey("twitter_account.id"))

    def __repr__(self):
        return "<Server(id='{}', server_name='{}', admin_name='{}')>"\
            .format(self.id, self.server_name, self.admin_name)


class TwitterAccount(Base):
    __tablename__ = "twitter_account"
    id = Column(Integer, primary_key=True)
    server_id = Column(Integer, ForeignKey("server.id"))
    admin_id = Column(String)
    twitter_name = Column(String)
    access_token = Column(String)
    access_secret = Column(String)

    def __repr__(self):
        return "<TwitterAccount(id='{}', server_id='{}', admin_id='{}')>"\
            .format(self.id, self.server_id, self.admin_id,
                    self.access_token, self.access_secret)


class Tweet(Base):
    __tablename__ = "tweet"
    id = Column(Integer, primary_key=True)
    tweet_content = Column(String(280))
    media_id = relationship("TweetMedia")
    tweet_url = Column(URLType)
    tweet_date = Column(DateTime)
    twitter_account_id = Column(Integer, ForeignKey("twitter_account.id"))

    def __repr__(self):
        return "<Tweet(id='{}', content='{}', url='{}')>"\
            .format(self.id, self.tweet_content, self.tweet_url)


class TweetMedia(Base):
    __tablename__ = "tweet_media"
    id = Column(Integer, primary_key=True)
    media_url = Column(URLType)
    tweet_id = Column(Integer, ForeignKey("tweet.id"))

    def __repr__(self):
        return "<TweetMedia(id='{}', media_url='{}')>"\
            .format(self.id, self.media_url)


# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
fileConfig(config.config_file_name)


# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline():
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url, target_metadata=target_metadata, literal_binds=True
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
