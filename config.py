import os
from pathlib import Path

basedir = Path(__file__).resolve().parent

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "Urika2021!")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL") or f"sqlite:///{basedir / 'instance' / 'redoku.sqlite'}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SITE_NAME = "Redoku"
