# models.py
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Team(db.Model):
    __tablename__ = "teams"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False, unique=True)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(32), nullable=False)  # "manager" or "employee"
    full_name = db.Column(db.String(128), nullable=True)
    team_id = db.Column(db.Integer, db.ForeignKey("teams.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    team = db.relationship("Team", backref=db.backref("members", lazy=True))

class CognitiveState(db.Model):
    __tablename__ = "states"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    stress = db.Column(db.Float, default=0.0)
    fatigue = db.Column(db.Float, default=0.0)
    attention = db.Column(db.Float, default=0.0)
    face = db.Column(db.String(64), nullable=True)
    voice = db.Column(db.String(64), nullable=True)

    user = db.relationship("User", backref=db.backref("states", lazy=True, order_by=timestamp.desc()))
