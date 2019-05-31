from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy import ForeignKey, Boolean, Table
import work.SociaBot.SociaBot.cogs.utils.settings as settings
from sqlalchemy_utils import URLType
from sqlalchemy.orm import sessionmaker, relationship

Base = declarative_base()
engine = create_engine(settings.DATABASE_URI)
Session = sessionmaker(engine)
session = Session()

server_user_table = Table('server_user', Base.metadata,
                          Column('server_id', Integer,
                                 ForeignKey("server.id")),
                          Column('user_id', Integer, ForeignKey("user.id"))
                          )

twitch_server_table = Table('twitch_server', Base.metadata,
                            Column('twitch_id', Integer,
                                   ForeignKey("twitch_account.id")),
                            Column('server_id', Integer,
                                   ForeignKey("server.id"))
                            )


class User(Base):
    __tablename__ = "user"
    id = Column(Integer, primary_key=True)
    discord_user_id = Column(String)
    discord_guild_ids = relationship("Server", secondary=server_user_table)
    dark_theme_enabled = Column(Boolean)
    user_twitter_account = Column(Integer, ForeignKey("twitter_account.id"))
    twitter_account_id = relationship(
        "TwitterAccount", foreign_keys=[user_twitter_account])
    twitch_account_id = relationship("TwitchAccount")
    language = Column(String)


class Server(Base):
    __tablename__ = "server"
    id = Column(Integer, primary_key=True)
    server_id = Column(String)
    server_name = Column(String)
    discord_admin_id = Column(String)
    users_id = relationship("User", secondary=server_user_table)
    admin_id = Column(Integer, ForeignKey("user.id"))
    admin_name = Column(String)
    twitch_notification_activated = relationship(
        "TwitchAccount", secondary=twitch_server_table)
    twitter_account_linked = Column(Integer, ForeignKey("twitter_account.id"))

    def __repr__(self):
        return "<Server(id='{}', server_name='{}', admin_name='{}')>".format(
            self.id, self.server_name, self.admin_name)


class TwitterAccount(Base):
    __tablename__ = "twitter_account"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("user.id"))
    twitter_name = Column(String)
    access_token = Column(String)
    access_secret = Column(String)
    account_user_id = Column(String)
    notification_enabled = Column(Boolean)

    def __repr__(self):
        return "<TWAccount(id='{}', server_id='{}', admin_id='{}')>".format(
            self.id, self.server_id, self.admin_id,
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
        return "<Tweet(id='{}', content='{}', url='{}')>".format(
            self.id, self.tweet_content, self.tweet_url)


class TweetMedia(Base):
    __tablename__ = "tweet_media"
    id = Column(Integer, primary_key=True)
    media_url = Column(URLType)
    tweet_id = Column(Integer, ForeignKey("tweet.id"))

    def __repr__(self):
        return "<TweetMedia(id='{}', media_url='{}')>".format(
            self.id, self.media_url)


class TwitchAccount(Base):
    __tablename__ = "twitch_account"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("user.id"))
    twitch_name = Column(String)
    twitch_id = Column(String)
    access_token = Column(String)
    refresh_token = Column(String)
    notification_activated_on = relationship(
        "Server", secondary=twitch_server_table)


Base.metadata.create_all(engine)
