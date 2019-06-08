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


class User(Base):
    __tablename__ = "user"
    id = Column(Integer, primary_key=True)
    discord_user_id = Column(String)
    discord_guild_ids = relationship("Server", secondary=server_user_table)
    dark_theme_enabled = Column(Boolean)
    twitter_account_id = Column(Integer, ForeignKey("twitter_account.id"))
    twitch_account_id = Column(Integer, ForeignKey("twitch_account.id"))
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
    twitch_account_linked = Column(Integer, ForeignKey("twitch_account.id"))
    twitter_account_linked = Column(Integer, ForeignKey("twitter_account.id"))
    twitter_notification_enabled = Column(Boolean)
    twitch_notification_enabled = Column(Boolean)

    def __repr__(self):
        return "<Server(id='{}', server_name='{}', admin_name='{}')>".format(
            self.id, self.server_name, self.admin_name)

    def _json(self):
        return {
            'id': self.id,
            'server_id': self.server_id,
            'server_name': self.server_name,
            'twitter_notification_enabled': self.twitter_notification_enabled,
            'twitch_notification_enabled': self.twitch_notification_enabled
        }


class TwitterAccount(Base):
    __tablename__ = "twitter_account"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("user.id"))
    twitter_name = Column(String)
    access_token = Column(String)
    access_secret = Column(String)
    account_user_id = Column(String)

    def __repr__(self):
        return "<TWAccount(id='{}', user_id='{}', name='{}')>".format(
            self.id, self.account_user_id, self.twitter_name)

    def _json(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'twitter_name': self.twitter_name,
            'access_token': self.access_token,
            'access_secret': self.access_secret,
            'account_user_id': self.account_user_id
        }


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


Base.metadata.create_all(engine)
