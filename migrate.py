# migrate.py
import os
from flask import Flask
from models import db, User
from auth import hash_password

APP_ROOT = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(APP_ROOT, "app.db")
DATABASE_URI = "sqlite:///" + DB_PATH

def create_app():
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URI
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    # secret key not needed for migration
    db.init_app(app)
    return app

def bootstrap():
    app = create_app()
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(username="manager").first():
            m = User(
                username="manager",
                password_hash=hash_password("manager123"),
                role="manager",
                full_name="Default Manager"
            )
            db.session.add(m)
            db.session.commit()
            print("Created manager account: username=manager password=manager123")
        else:
            print("Manager account already exists.")

if __name__ == "__main__":
    bootstrap()
