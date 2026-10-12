import time

from config import today
from database import db
from models import Sample

def update_incubation_statuses(app):
    with app.app_context():
        try:
            count = Sample.query.filter(
                Sample.incubation_status == "Incubating",
                Sample.incubation_ends_on <= today(),
            ).update({Sample.incubation_status: "Need to check"}, synchronize_session=False)
            db.session.commit()
            return count
        except Exception:
            db.session.rollback()
            raise


def background_job(app):
    while True:
        try:
            count = update_incubation_statuses(app)
            if count:
                app.logger.warning("[Background job] Some plates statues has changed", count)
        except Exception:
            app.logger.exception("[Background job] Failed to refresh statuses, will try again in 30 seconds")
        time.sleep(10)
        
