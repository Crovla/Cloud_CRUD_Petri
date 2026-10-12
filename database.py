from datetime import timedelta

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect, text


db = SQLAlchemy()

def initialize_database(app):
    from models import Sample

    with app.app_context():
        db.create_all()


