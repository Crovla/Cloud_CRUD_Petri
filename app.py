import os
import threading
import time
import uuid
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
from sqlalchemy import inspect, text

from flask import (Flask, Response, abort, flash, jsonify, redirect,
                   render_template, request, url_for)
from flask_sqlalchemy import SQLAlchemy

import storage

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-only")
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "DATABASE_URL", "sqlite:///samples.db").replace("postgres://", "postgresql://", 1)
db = SQLAlchemy(app)
APP_TIMEZONE = ZoneInfo(os.environ.get("APP_TIMEZONE", "Europe/Vilnius"))
STATUSES = ("Incubating", "Need to check", "Done")

def today():
    return datetime.now(APP_TIMEZONE).date()

ALLOWED = {"png", "jpg", "jpeg"}

class Sample(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)          
    colony_count = db.Column(db.Integer, nullable=False)     
    temperature = db.Column(db.Float, nullable=False)       
    is_pathogenic = db.Column(db.Boolean, default=False)    
    image_key = db.Column(db.String(120))                   
    incubation_started_on = db.Column(db.Date, nullable=False)
    incubation_ends_on = db.Column(db.Date, nullable=False)
    incubation_status = db.Column(db.String(30), nullable=False, default="Incubating")

    def to_dict(self):
        return {
            "id": self.id, "name": self.name, 
            "colony_count": self.colony_count,
            "temperature": self.temperature,
            "is_pathogenic": self.is_pathogenic,
            "incubation_started_on": self.incubation_started_on.isoformat(),
            "incubation_ends_on": self.incubation_ends_on.isoformat(),
            "incubation_status": self.incubation_status,
            "image_url": url_for("serve_file", key=self.image_key, _external=True)
            if self.image_key else None,
        }


def initialize_database():
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


initialize_database()

def validate(data):
    clean, errors = {}, {}

    raw_name = data.get("name")
    name = raw_name.strip() if isinstance(raw_name, str) else ""
    if 2 <= len(name) <= 80:
        clean["name"] = name
    else:
        errors["name"] = "Name must be 2-80 characters."

    try:
        count = int(str(data.get("colony_count")).strip())
        if count < 0:
            raise ValueError
        clean["colony_count"] = count
    except ValueError:
        errors["colony_count"] = "Colony count must be a whole number, 0 or more."

    try:
        temp = float(str(data.get("temperature")).strip().replace(",", "."))
        if not -20 <= temp <= 100:
            raise ValueError
        clean["temperature"] = temp
    except ValueError:
        errors["temperature"] = "Temperature must be a number between -20 and 100."

    flag = data.get("is_pathogenic", False)
    if isinstance(flag, str):
        value = flag.lower()
        if value in ("on", "true", "1", "yes"):
            flag = True
        elif value in ("off", "false", "0", "no", ""):
            flag = False
    if isinstance(flag, bool):
        clean["is_pathogenic"] = flag
    else:
        errors["is_pathogenic"] = "Must be true or false."

    for field in ("incubation_started_on", "incubation_ends_on"):
        try:
            clean[field] = date.fromisoformat(str(data.get(field)))
        except ValueError:
            errors[field] = "Enter a valid date (YYYY-MM-DD)."
    start, end = clean.get("incubation_started_on"), clean.get("incubation_ends_on")
    if start and start > today():
        errors["incubation_started_on"] = "The start of incubation cannot be in the future."
    if start and end and end < start:
        errors["incubation_ends_on"] = "The incubation end cannot come before the beginning."
    status = data.get("incubation_status", "Incubating")
    if status not in STATUSES:
        errors["incubation_status"] = "Select a valid status."
    else:
        clean["incubation_status"] = status
    return clean, errors


# Background job
def update_incubation_statuses():
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


def background_job():
    while True:
        try:
            count = update_incubation_statuses()
            if count:
                app.logger.warning("[Background] Have to check: %s plates", count)
        except Exception:
            app.logger.exception("[Background] Failed to refresh statuses, will try again in 30 seconds")
        time.sleep(30)


def remove(sample):
    if sample.image_key:
        storage.delete(sample.image_key)
    db.session.delete(sample)
    db.session.commit()


# ---------- Web pages ----------
@app.route("/")
def index():
    return render_template("index.html", samples=Sample.query.order_by(Sample.id.desc()).all())


@app.route("/samples/<int:id>")
def detail(id):
    return render_template("detail.html", s=db.get_or_404(Sample, id))


@app.route("/samples/new", methods=["GET", "POST"])
@app.route("/samples/<int:id>/edit", methods=["GET", "POST"])
def sample_form(id=None):
    sample = db.get_or_404(Sample, id) if id else None
    errors = {}
    if request.method == "POST":
        values = request.form
        clean, errors = validate(values)
        file = request.files.get("image")
        has_file = bool(file and file.filename)
        if has_file and file.filename.rsplit(".", 1)[-1].lower() not in ALLOWED:
            errors["image"] = "Only .png, .jpg or .jpeg files are allowed."
        if not errors:
            if sample is None:
                sample = Sample(**clean)
                db.session.add(sample)
            else:
                for key, val in clean.items():
                    setattr(sample, key, val)
            if has_file:
                if sample.image_key:
                    storage.delete(sample.image_key)
                sample.image_key = uuid.uuid4().hex + "." + file.filename.rsplit(".", 1)[-1].lower()
                storage.save(sample.image_key, file.read(), file.mimetype)
            db.session.commit()
            flash("Sample saved.")
            return redirect(url_for("detail", id=sample.id))
    else:
        values = sample.to_dict() if sample else {}
    return render_template("form.html", v=values, errors=errors, editing=sample is not None, statuses=STATUSES)


@app.post("/samples/<int:id>/delete")
def delete(id):
    remove(db.get_or_404(Sample, id))
    flash("Sample deleted.")
    return redirect(url_for("index"))


@app.route("/files/<key>")
def serve_file(key):
    data = storage.load(key)
    if data is None:
        abort(404)
    return Response(data, mimetype="image/png" if key.endswith("png") else "image/jpeg")


# ---------- Public JSON API ----------
@app.get("/api/samples")
def api_list():
    return jsonify([s.to_dict() for s in Sample.query.order_by(Sample.id).all()])


@app.get("/api/samples/<int:id>")
def api_get(id):
    return jsonify(db.get_or_404(Sample, id).to_dict())


@app.post("/api/samples")
def api_create():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify(errors={"body": "Expected a JSON object."}), 400
    clean, errors = validate(data)
    if errors:
        return jsonify(errors=errors), 400
    sample = Sample(**clean)
    db.session.add(sample)
    db.session.commit()
    return jsonify(sample.to_dict()), 201


@app.put("/api/samples/<int:id>")
def api_update(id):
    sample = db.get_or_404(Sample, id)
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify(errors={"body": "Expected a JSON object."}), 400
    clean, errors = validate(data)
    if errors:
        return jsonify(errors=errors), 400
    for key, val in clean.items():
        setattr(sample, key, val)
    db.session.commit()
    return jsonify(sample.to_dict())


@app.delete("/api/samples/<int:id>")
def api_delete(id):
    remove(db.get_or_404(Sample, id))
    return "", 204


# Use one Gunicorn worker without --preload (see Procfile).
if os.environ.get("BACKGROUND_ENABLED", "1") == "1":
    threading.Thread(target=background_job, name="incubation-check", daemon=True).start()

if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)
