from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
import sqlite3
import csv
import os
from io import StringIO, BytesIO
from datetime import datetime
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "hackverse_2026_secret"

DB_NAME = "hackverse.db"

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "cheyaa_06"

UPLOAD_FOLDER = os.path.join("static", "uploads")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

DOMAINS = [
    "Drones",
    "EV",
    "Software",
    "Hardware",
    "Cybersecurity",
    "FinTech & BioTech"
]

EVENT_DATE = "October 18, 2026"
VENUE = "NSRIT, Visakhapatnam"
COLLEGE_NAME = "Nadimpalli Satyanarayana Raju Institute of Technology (NSRIT)"
TEAM_SIZE = "Minimum 2 Members • Maximum 4 Members"
REGISTRATION_FEE = "₹XXX per team"
FACULTY_COORDINATORS = [
    "Dr. Faculty Coordinator 1",
    "Mr./Ms. Faculty Coordinator 2"
]


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS participants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            team_name TEXT NOT NULL,
            leader_name TEXT NOT NULL,
            college_name TEXT NOT NULL,
            phone TEXT NOT NULL,
            email TEXT,
            domain TEXT NOT NULL,
            members TEXT,
            idea_title TEXT,
            idea_description TEXT,
            utr_id TEXT,
            payment_screenshot TEXT,
            created_at TEXT NOT NULL
        )
    """)

    # Safe upgrade
    try:
        cur.execute("ALTER TABLE participants ADD COLUMN utr_id TEXT")
    except:
        pass

    try:
        cur.execute("ALTER TABLE participants ADD COLUMN payment_screenshot TEXT")
    except:
        pass

    conn.commit()
    conn.close()


@app.route("/")
def index():
    return render_template(
        "index.html",
        domains=DOMAINS,
        event_date=EVENT_DATE,
        venue=VENUE,
        college_name=COLLEGE_NAME,
        team_size=TEAM_SIZE,
        registration_fee=REGISTRATION_FEE,
        faculty_coordinators=FACULTY_COORDINATORS
    )


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        team_name = request.form.get("team_name", "").strip()
        leader_name = request.form.get("leader_name", "").strip()
        college_name = request.form.get("college_name", "").strip()
        phone = request.form.get("phone", "").strip()
        email = request.form.get("email", "").strip()
        domain = request.form.get("domain", "").strip()
        members = request.form.get("members", "").strip()
        idea_title = request.form.get("idea_title", "").strip()
        idea_description = request.form.get("idea_description", "").strip()
        utr_id = request.form.get("utr_id", "").strip()

        if not team_name or not leader_name or not college_name or not phone or not domain:
            flash("Please fill all required fields.")
            return redirect(url_for("register"))

        if not utr_id:
            flash("Please enter UTR ID.")
            return redirect(url_for("register"))

        file = request.files.get("payment_screenshot")
        payment_filename = ""

        if file and file.filename:
            if allowed_file(file.filename):
                original_name = secure_filename(file.filename)
                timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                payment_filename = f"{timestamp}_{original_name}"
                file.save(os.path.join(app.config["UPLOAD_FOLDER"], payment_filename))
            else:
                flash("Invalid file format.")
                return redirect(url_for("register"))
        else:
            flash("Upload payment screenshot.")
            return redirect(url_for("register"))

        conn = get_db()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO participants
            (
                team_name, leader_name, college_name, phone, email, domain,
                members, idea_title, idea_description,
                utr_id, payment_screenshot, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            team_name, leader_name, college_name, phone, email, domain,
            members, idea_title, idea_description,
            utr_id, payment_filename,
            datetime.now().strftime("%d-%m-%Y %I:%M %p")
        ))

        conn.commit()
        conn.close()

        return redirect(url_for("success", team=team_name))

    return render_template(
        "register.html",
        domains=DOMAINS,
        event_date=EVENT_DATE,
        venue=VENUE,
        college_name=COLLEGE_NAME,
        team_size=TEAM_SIZE,
        registration_fee=REGISTRATION_FEE,
        faculty_coordinators=FACULTY_COORDINATORS
    )


@app.route("/success")
def success():
    team = request.args.get("team", "Your Team")
    return render_template("success.html", team=team)


@app.route("/admin", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session["admin"] = True
            return redirect(url_for("admin_dashboard"))

        flash("Invalid login")

    return render_template("admin_login.html")


@app.route("/admin/dashboard")
def admin_dashboard():
    if not session.get("admin"):
        return redirect(url_for("admin_login"))

    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM participants")
    total = cur.fetchone()[0]

    cur.execute("SELECT domain, COUNT(*) FROM participants GROUP BY domain")
    domain_counts = cur.fetchall()

    cur.execute("SELECT * FROM participants ORDER BY id DESC")
    participants = cur.fetchall()

    conn.close()

    return render_template(
        "admin_dashboard.html",
        total=total,
        domain_counts=domain_counts,
        participants=participants
    )
@app.route("/admin/download")
def download_csv():
    if not session.get("admin"):
        return redirect(url_for("admin_login"))

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM participants ORDER BY id DESC")
    rows = cur.fetchall()
    conn.close()

    output = StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "ID", "Team Name", "Leader Name", "College Name", "Phone", "Email",
        "Domain", "Members", "Idea Title", "Idea Description",
        "UTR ID", "Payment Screenshot", "Created At"
    ])

    for row in rows:
        writer.writerow([
            row["id"], row["team_name"], row["leader_name"], row["college_name"],
            row["phone"], row["email"], row["domain"], row["members"],
            row["idea_title"], row["idea_description"],
            row["utr_id"], row["payment_screenshot"], row["created_at"]
        ])

    mem = BytesIO(output.getvalue().encode("utf-8"))
    mem.seek(0)

    return send_file(
        mem,
        mimetype="text/csv",
        as_attachment=True,
        download_name="hackverse_participants.csv"
    )


@app.route("/logout")
def logout():
    session.pop("admin", None)
    return redirect(url_for("admin_login"))


if __name__ == "__main__":
    init_db()
    app.run(debug=True)