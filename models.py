from flask import url_for
from database import db

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