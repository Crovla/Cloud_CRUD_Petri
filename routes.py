import uuid

from flask import (
    Response,
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)

import storage
from config import ALLOWED, STATUSES
from database import db
from models import Sample
from validation import validate

def remove(sample):
    if sample.image_key:
        storage.delete(sample.image_key)
    db.session.delete(sample)
    db.session.commit()
    
def routes(app):
    @app.route("/")
    def index():
        return render_template("index.html", samples=Sample.query.order_by(Sample.id.desc()).all())


    @app.route("/samples/<int:id>")
    def detail(id):
        return render_template("detail.html", s=db.get_or_404(Sample, id))


    @app.route("/samples/new", methods=["GET", "POST"])
    def create_sample():
        errors = {}
        values = {}

        if request.method == "POST":
            values = request.form
            clean, errors = validate(values)

            file = request.files.get("image")
            has_file = bool(file and file.filename)

            if has_file and file.filename.rsplit(".", 1)[-1].lower() not in ALLOWED:
                errors["image"] = "Only .png, .jpg or .jpeg files are allowed."

            if not errors:
                sample = Sample(**clean)
                db.session.add(sample)

                if has_file:
                    sample.image_key = uuid.uuid4().hex + "." + file.filename.rsplit(".", 1)[-1].lower()
                    storage.save(sample.image_key, file.read(), file.mimetype)

                db.session.commit()

                flash("Sample created.")
                return redirect(url_for("detail", id=sample.id))

        return render_template(
            "form.html",
            v=values,
            errors=errors,
            editing=False,
            statuses=STATUSES
        )


    @app.route("/samples/<int:id>/edit", methods=["GET", "POST"])
    def edit_sample(id):
        sample = db.get_or_404(Sample, id)
        errors = {}

        if request.method == "POST":
            values = request.form
            clean, errors = validate(values)

            file = request.files.get("image")
            has_file = bool(file and file.filename)

            if has_file and file.filename.rsplit(".", 1)[-1].lower() not in ALLOWED:
                errors["image"] = "Only .png, .jpg or .jpeg files are allowed."

            if not errors:
                for key, val in clean.items():
                    setattr(sample, key, val)

                if has_file:
                    if sample.image_key:
                        storage.delete(sample.image_key)

                    sample.image_key = uuid.uuid4().hex + "." + file.filename.rsplit(".", 1)[-1].lower()
                    storage.save(sample.image_key, file.read(), file.mimetype)

                db.session.commit()

                flash("Sample updated.")
                return redirect(url_for("detail", id=sample.id))

        else:
            values = sample.to_dict()

        return render_template(
            "form.html",
            v=values,
            errors=errors,
            editing=True,
            statuses=STATUSES
        )

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
