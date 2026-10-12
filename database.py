from datetime import timedelta

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect, text


db = SQLAlchemy()

def initialize_database(app):
    from models import Sample
    with app.app_context():
        db.create_all()
        columns = {c["name"] for c in inspect(db.engine).get_columns("sample")}
        additions = {"incubation_started_on": "DATE",
                     "incubation_ends_on": "DATE",
                     "incubation_status": "VARCHAR(30)"}
        with db.engine.begin() as connection:
            for name, sql_type in additions.items():
                if name not in columns:
                    connection.execute(text(f"ALTER TABLE sample ADD COLUMN {name} {sql_type}"))
        for sample in Sample.query.filter(db.or_(
                Sample.incubation_started_on.is_(None),
                Sample.incubation_ends_on.is_(None),
                Sample.incubation_status.is_(None))).all():
            sample.incubation_started_on = sample.incubation_started_on
            sample.incubation_ends_on = sample.incubation_ends_on or (sample.incubation_started_on + timedelta(days=7))
            sample.incubation_status = sample.incubation_status or "Incubating"
        db.session.commit()


