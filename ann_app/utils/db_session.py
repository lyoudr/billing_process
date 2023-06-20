from flask import current_app 
from sqlalchemy import create_engine 
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager


@contextmanager
def session_scope():
    with current_app.app_context():
        # Create SQLAlchemy engine
        engine = create_engine(current_app.config["SQLALCHEMY_DATABASE_URI"])
        # Create a session factory
        Session = sessionmaker(bind=engine)
        
        session = Session()
        try:
            yield session 
            session.commit()
        except:
            session.rollback()
            raise 
        finally:
            session.close()