from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
import cogs.utils.settings as settings
from sqlalchemy_utils import URLType
from sqlalchemy.orm import sessionmaker, relationship

Base = declarative_base()
engine = create_engine(settings.DATABASE_URI)
Session = sessionmaker(engine)
session = Session()


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


Base.metadata.create_all(engine)
