# app_full.py
import os
import time
import threading
import datetime
from flask import (Flask, render_template, request, redirect, url_for, session,
                   jsonify, send_file, abort)

from models import db, User, Team, CognitiveState
from auth import hash_password, check_password
from capture.face_module import get_face_emotion
from capture.voice_module import get_voice_emotion
from capture.fusion_module import compute_cognitive_state

APP_ROOT = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(APP_ROOT, "app.db")
DATABASE_URI = "sqlite:///" + DB_PATH

app = Flask(__name__, static_folder='static', template_folder='templates')
app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URI
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
# for demo change this; when packaging generate a random secret
app.secret_key = "demo-secret-key-change-me"

db.init_app(app)

# --- capture thread management ---
capture_threads = {}
capture_lock = threading.Lock()

def start_employee_capture(username):
    with capture_lock:
        if username in capture_threads:
            return
        stop = {"stop": False}
        def loop():
            print(f"[capture] Starting capture for {username}")
            # run until stop flag flipped
            while not stop["stop"]:
                t0 = time.time()

                # All DB reads/writes must run inside app.app_context()
                try:
                    with app.app_context():
                        user = User.query.filter_by(username=username).first()
                except Exception as e:
                    print("DB read error in capture (context):", e)
                    user = None

                if not user:
                    # no user found -> exit the loop
                    break

                # capture (safe stubs)
                face = get_face_emotion()
                voice = get_voice_emotion()

                fused = compute_cognitive_state(face, voice)

                try:
                    with app.app_context():
                        state = CognitiveState(
                            user_id=user.id,
                            timestamp=datetime.datetime.utcnow(),
                            stress=fused["stress"],
                            fatigue=fused["fatigue"],
                            attention=fused["attention"],
                            face=face,
                            voice=voice,
                        )
                        db.session.add(state)
                        db.session.commit()
                except Exception as e:
                    # rollback and keep running (don't crash thread)
                    try:
                        with app.app_context():
                            db.session.rollback()
                    except Exception:
                        pass
                    print("DB save error in capture (context):", e)

                # sleep to align ~60s but check stop flag frequently
                elapsed = time.time() - t0
                to_sleep = max(0, 60 - elapsed)
                slept = 0.0
                while not stop["stop"] and slept < to_sleep:
                    time.sleep(min(1.0, to_sleep - slept))
                    slept += min(1.0, to_sleep - slept)

            print(f"[capture] Stopped capture for {username}")

        th = threading.Thread(target=loop, daemon=True)
        capture_threads[username] = {"thread": th, "stop": stop}
        th.start()


def stop_employee_capture(username):
    with capture_lock:
        entry = capture_threads.get(username)
        if entry:
            entry["stop"]["stop"] = True
            # thread will exit; remove entry
            del capture_threads[username]

# ---------- Routes ----------

@app.route("/")
def index():
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username","").strip()
        password = request.form.get("password","")
        user = User.query.filter_by(username=username).first()
        if user and check_password(password, user.password_hash):
            session["username"] = username
            session["role"] = user.role
            if user.role == "employee":
                start_employee_capture(username)
                return redirect(url_for("employee_dashboard", username=username))
            return redirect(url_for("manager_dashboard"))
        else:
            return render_template("login.html", error="Invalid credentials")
    return render_template("login.html", error=None)

@app.route("/logout")
def logout():
    username = session.get("username")
    if username and session.get("role") == "employee":
        stop_employee_capture(username)
    session.clear()
    return redirect(url_for("login"))

# Manager UI
@app.route("/manager")
def manager_dashboard():
    if session.get("role") != "manager":
        return redirect(url_for("login"))
    teams = Team.query.all()
    users = {u.username: {"role": u.role, "full_name": u.full_name, "team_id": u.team_id} for u in User.query.all()}
    teams_data = []
    for t in teams:
        teams_data.append({"id": t.id, "name": t.name, "employees": [m.username for m in t.members]})
    return render_template("manager.html", teams=teams_data, users=users)

@app.route("/api/teams")
def api_teams():
    if session.get("role") != "manager":
        return jsonify({"error":"unauthorized"}), 401
    teams = Team.query.all()
    teams_data = [{"id": t.id, "name": t.name, "employees":[m.username for m in t.members]} for t in teams]
    return jsonify({"teams": teams_data})

@app.route("/api/users")
def api_users():
    if session.get("role") != "manager":
        return jsonify({"error":"unauthorized"}), 401
    users = User.query.all()
    out = {u.username: {"role":u.role, "full_name":u.full_name, "team_id":u.team_id} for u in users}
    return jsonify(out)

@app.route("/api/team", methods=["POST"])
def api_create_team():
    if session.get("role") != "manager":
        return jsonify({"error":"unauthorized"}), 401
    body = request.json or {}
    name = body.get("name","").strip()
    if not name:
        return jsonify({"error":"missing name"}), 400
    t = Team(name=name)
    db.session.add(t); db.session.commit()
    return jsonify({"ok": True, "id": t.id})

@app.route("/api/team/<int:team_id>", methods=["DELETE"])
def api_delete_team(team_id):
    if session.get("role") != "manager":
        return jsonify({"error":"unauthorized"}), 401
    t = Team.query.get(team_id)
    if not t:
        return jsonify({"error":"not found"}), 404
    for m in t.members:
        m.team_id = None
    db.session.delete(t)
    db.session.commit()
    return jsonify({"ok": True})

@app.route("/api/employee", methods=["POST"])
def api_add_employee():
    if session.get("role") != "manager":
        return jsonify({"error":"unauthorized"}), 401
    body = request.json or {}
    username = body.get("username","").strip()
    password = body.get("password","").strip()
    full_name = body.get("name","").strip()
    team_id = body.get("team_id")
    if not username or not password:
        return jsonify({"error":"missing username or password"}), 400
    if User.query.filter_by(username=username).first():
        return jsonify({"error":"user exists"}), 400
    h = hash_password(password)
    user = User(username=username, password_hash=h, role="employee", full_name=full_name, team_id=team_id)
    db.session.add(user)
    db.session.commit()
    return jsonify({"ok": True})

@app.route("/api/employee/<username>", methods=["DELETE"])
def api_delete_employee(username):
    if session.get("role") != "manager":
        return jsonify({"error":"unauthorized"}), 401
    u = User.query.filter_by(username=username).first()
    if not u:
        return jsonify({"error":"not found"}), 404
    stop_employee_capture(username)
    CognitiveState.query.filter_by(user_id=u.id).delete()
    db.session.delete(u)
    db.session.commit()
    return jsonify({"ok": True})

@app.route("/manager/employee/<username>")
def manager_view_employee(username):
    if session.get("role") != "manager":
        return redirect(url_for("login"))
    u = User.query.filter_by(username=username).first()
    if not u:
        return "Not found", 404
    states = CognitiveState.query.filter_by(user_id=u.id).order_by(CognitiveState.timestamp.desc()).limit(500).all()
    states_json = [{"time": s.timestamp.strftime("%Y-%m-%d %H:%M:%S"), "stress": s.stress, "fatigue": s.fatigue, "attention": s.attention, "face":s.face, "voice":s.voice} for s in states]
    return render_template("employee_history.html", username=username, history=states_json)

# Employee dashboard
@app.route("/employee/<username>")
def employee_dashboard(username):
    if session.get("username") != username or session.get("role") != "employee":
        return redirect(url_for("login"))
    return render_template("employee.html", username=username)

@app.route("/api/state/<username>")
def api_state_user(username):
    # employee can only fetch their own; manager can fetch any
    if session.get("role") == "employee" and session.get("username") != username:
        return jsonify({"error":"unauthorized"}), 401
    u = User.query.filter_by(username=username).first()
    if not u:
        return jsonify({"error":"not found"}), 404
    s = CognitiveState.query.filter_by(user_id=u.id).order_by(CognitiveState.timestamp.desc()).first()
    if not s:
        return jsonify({"status":"no-data"}), 202
    return jsonify({
        "time": s.timestamp.strftime("%H:%M:%S"),
        "face": s.face,
        "voice": s.voice,
        "stress": s.stress,
        "fatigue": s.fatigue,
        "attention": s.attention
    })

@app.route("/api/history/<username>")
def api_history(username):
    if session.get("role") == "employee" and session.get("username") != username:
        return jsonify({"error":"unauthorized"}), 401
    u = User.query.filter_by(username=username).first()
    if not u:
        return jsonify([])
    states = CognitiveState.query.filter_by(user_id=u.id).order_by(CognitiveState.timestamp.asc()).all()
    return jsonify([{"time":s.timestamp.strftime("%Y-%m-%d %H:%M:%S"), "stress":s.stress, "fatigue":s.fatigue, "attention":s.attention, "face":s.face, "voice":s.voice} for s in states])

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    print("Starting Cogni (local) — visit http://127.0.0.1:5000/login")
    # important: disable reloader so background threads persist
    app.run(debug=True, use_reloader=False)
