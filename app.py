import os
import threading

from flask import Flask

import config
from background import background_job
from database import db, initialize_database
from routes import routes


app = Flask(__name__)

app.config.from_object(config)

db.init_app(app)

routes(app)

initialize_database(app)

if os.environ.get("BACKGROUND_ENABLED", "1") == "1":
    threading.Thread(
        target=background_job,
        args=(app,),
        name="incubation-check",
        daemon=True,
    ).start()


if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)