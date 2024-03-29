from sqlalchemy import create_engine, Column, String, Integer, Sequence, TIMESTAMP, Boolean, Enum, select, ForeignKey, update
from urllib.parse import urlparse, parse_qs
from sqlalchemy.orm import sessionmaker, relationship, joinedload, declarative_base
from typing import Any, TypedDict, cast
from sqlalchemy.sql import func
from typing import Optional
from loguru import logger
from config import config
  
Base = declarative_base()




class Playlist(Base):
  __tablename__ = 'playlists'
  id = Column(Integer, autoincrement=True, primary_key=True)
  title = Column(String, default=None)
  # vidtype = Column(Enum('video', 'audio', name='vidtype'), default='audio')
  url = Column(String, unique=True)
  queue_status = Column(Enum('queued', 'in_progress', 'completed', name='queue_status'), default='queued')
  create_time = Column(TIMESTAMP, default=func.now())
  downloaded_time = Column(TIMESTAMP, default=None)
  downloaded_items = relationship('Downloaded', back_populates='playlist')

class Downloaded(Base):
  __tablename__ = 'downloaded'
  id = Column(Integer, autoincrement=True, primary_key=True)
  title = Column(String)
  playlist_url = Column(String, ForeignKey('playlists.url'))
  url = Column(String)
  path = Column(String)
  elapsed = Column(String)
  create_time = Column(TIMESTAMP, default=func.now())
  playlist = relationship('Playlist', back_populates='downloaded_items')

def spliturl(url: list):
  """Splits urls the exact same way as the main.py script for consistant url grabbing

  Args:
      url (string): Youtube url Eg: https://www.youtube.com/watch?v=sVJEaYNOUNw&t=162s

  Returns:
      string: End of youtube url
  """
  parsed_url = urlparse(url) #type: ignore

  query_params = parse_qs(parsed_url.query)
  video_id = query_params.get('v')
  playlist_id = query_params.get('list')
  if not playlist_id == None:
      url.append(playlist_id)
  else:
      url.append(video_id)
  return url

class Database:
    engine = None

    def __init__(self):
        self.connect(config.db.host, config.db.port, config.db.user, config.db.password, config.db.db) #type: ignore

    def connect(self, host, port, user, password, database):
        self.engine = create_engine(
            f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{database}",
            echo=False,
            connect_args={"options": "-c timezone=utc"}
        )

        self.session = sessionmaker(
            bind=self.engine, expire_on_commit=False
        )

    def QueueNotDone(self):
      with self.session() as session:
        for item in session.execute(select(Playlist).filter(Playlist.queue_status == 'queued').order_by(Playlist.create_time.asc())).scalars().all():
          logger.info(f'Retrieved URL from database: {item.url}')
          yield item

    def mark_playlist_downloaded(self, qurl, title):
      try:
        logger.debug(qurl)
        stmt = (
            update(Playlist)
            .where(Playlist.url == qurl)
            .values(
              title=title,
              queue_status='completed',
              downloaded_time=func.now()
            )
        )
        with self.session() as session:
          with session.begin():
            session.execute(stmt)
            logger.info(f'Marked playlist "{qurl}" as downloaded')
      except Exception as e:
        logger.error(e)
        
    def mark_video_downloaded(self, playlist_url, url, title, download_path, elapsed):
      with self.session() as session:
        with session.begin():
          new_download = Downloaded(
            title=title,
            playlist_url=playlist_url,
            url=url,
            path=download_path,
            elapsed=elapsed,
            )
          session.add(new_download)
          session.commit()

    # def new_queue(self, url, vidtype: Optional[str]):
    def new_queue(self, url):
      with self.session() as session:
        with session.begin():
          # new_queue = Playlist(title=None, vidtype=vidtype, url=url, queue_status='queued')
          new_queue = Playlist(title=None, url=url, queue_status='queued')
          session.add(new_queue)
          session.commit()

    def db_create(self):
      with self.engine.begin() as conn: #type: ignore
        Base.metadata.create_all(conn)

    def reconnect(self):
      self.session.close_all()
      self.connect(config.db.host, config.db.port, config.db.user, config.db.password, config.db.db) #type: ignore

    def __enter__(self):
      return self

    def __exit__(self, exc_type, exc_value, traceback):
      self.session.close_all()
      if exc_type is not None:
        raise






