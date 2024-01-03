import os
from typing import Annotated

from fastapi import Depends
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.orm import declarative_base

DATABASE_URI = os.getenv("DATABASE_URI")

Base = declarative_base()

engine = create_engine(DATABASE_URI)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


DatabaseDependency = Annotated[Session, Depends(get_db)]
