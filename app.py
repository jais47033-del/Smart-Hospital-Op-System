from flask import (
    Flask, render_template, request,
    redirect, url_for, session, send_file
)

from functools import wraps
import sqlite3
import qrcode
import os
import csv
import io


app = Flask(
    __name__,
    template_folder="templates",
    static_folder="static"
)

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "smartcare-development-secret-key"
)

DATABASE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "hospital.db"
)

QR_FOLDER = os.path.join(
    app.root_path, "static", "qr_codes"
)

os.makedirs(QR_FOLDER, exist_ok=True)


# ---------------- DATABASE CONNECTION ----------------

def get_db_connection():

    conn = sqlite3.connect(DATABASE, timeout=30)

    conn.row_factory = sqlite3.Row

    conn.execute("PRAGMA busy_timeout = 30000")

    return conn


# ---------------- CREATE DATABASE ----------------

def create_table():

    conn = get_db_connection()

    try:

        conn.execute("PRAGMA journal_mode = WAL")

        conn.execute("""
            CREATE TABLE IF NOT EXISTS appointments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                department TEXT NOT NULL,
                token INTEGER NOT NULL,
                status TEXT DEFAULT 'Waiting',
                doctor_id INTEGER
            )
        """)

        conn.commit()

    finally:

        conn.close()


create_table()


# ---------------- ADMIN LOGIN SETTINGS ----------------

ADMIN_USERNAME = os.environ.get(
    "ADMIN_USERNAME", "admin"
)

ADMIN_PASSWORD = os.environ.get(
    "ADMIN_PASSWORD", "admin123"
)


def admin_required(function):

    @wraps(function)
    def wrapper(*args, **kwargs):

        if not session.get("admin_logged_in"):
            return redirect(url_for("login"))

        return function(*args, **kwargs)

    return wrapper


# ---------------- QUEUE POSITION ----------------

def get_queue_position(patient):

    conn = get_db_connection()

    try:

        waiting = conn.execute("""
            SELECT COUNT(*)
            FROM appointments
            WHERE department = ?
            AND status = 'Waiting'
        """, (patient["department"],)).fetchone()[0]

        position = 0

        if patient["status"] == "Waiting":

            position = conn.execute("""
                SELECT COUNT(*)
                FROM appointments
                WHERE department = ?
                AND status = 'Waiting'
                AND id <= ?
            """, (
                patient["department"],
                patient["id"]
            )).fetchone()[0]

        estimated_wait = max(position - 1, 0) * 10

        return {
            "position": position,
            "waiting": waiting,
            "estimated_wait": estimated_wait
        }

    finally:

        conn.close()


# ---------------- HOME PAGE ----------------

@app.route("/")
def home():

    conn = get_db_connection()

    try:

        current_token = conn.execute("""
            SELECT token
            FROM appointments
            WHERE status = 'Serving'
            ORDER BY id DESC
            LIMIT 1
        """).fetchone()

        waiting = conn.execute("""
            SELECT COUNT(*)
            FROM appointments
            WHERE status = 'Waiting'
        """).fetchone()[0]

        completed = conn.execute("""
            SELECT COUNT(*)
            FROM appointments
            WHERE status = 'Completed'
        """).fetchone()[0]

    finally:

        conn.close()

    return render_template(
        "index.html",
        current_token=current_token["token"] if current_token else 0,
        waiting=waiting,
        completed=completed
    )


# ---------------- PATIENT BOOKING ----------------

@app.route("/booking", methods=["GET", "POST"])
def booking():

    if request.method == "POST":

        patient_name = request.form.get(
            "name", ""
        ).strip()

        department = request.form.get(
            "department", ""
        ).strip()

        if not patient_name or not department:
            return "Please enter patient name and department."

        conn = get_db_connection()

        try:

            conn.execute("BEGIN IMMEDIATE")

            last_token = conn.execute("""
                SELECT MAX(token)
                FROM appointments
            """).fetchone()[0]

            token = (last_token or 0) + 1

            conn.execute("""
                INSERT INTO appointments
                (name, department, token, status, doctor_id)
                VALUES (?, ?, ?, 'Waiting', NULL)
            """, (
                patient_name,
                department,
                token
            ))

            conn.commit()

        except Exception:

            conn.rollback()
            raise

        finally:

            conn.close()

        # Generate QR code

        tracking_url = url_for(
            "track_token",
            token=token,
            _external=True
        )

        qr = qrcode.make(tracking_url)

        qr_path = os.path.join(
            QR_FOLDER,
            f"token_{token}.png"
        )

        qr.save(qr_path)

        return render_template(
            "booking.html",
            token=token,
            qr_code=f"qr_codes/token_{token}.png",
            patient_name=patient_name,
            department=department,
            success=True
        )

    return render_template("booking.html")


# ---------------- TRACKING PAGE ----------------

@app.route("/track", methods=["GET", "POST"])
def track_page():

    token = request.values.get(
        "token", ""
    ).strip()

    if not token:

        return render_template(
            "track.html",
            patient=None,
            token=None,
            position=0,
            waiting=0,
            estimated_wait=0
        )

    try:

        token = int(token)

    except ValueError:

        return "Please enter a valid token number.", 400

    return redirect(
        url_for("track_token", token=token)
    )


# ---------------- TRACK PATIENT TOKEN ----------------

@app.route("/track/<int:token>", methods=["GET", "POST"])
def track_token(token):

    conn = get_db_connection()

    try:

        patient = conn.execute("""
            SELECT *
            FROM appointments
            WHERE token = ?
        """, (token,)).fetchone()

    finally:

        conn.close()

    if patient is None:
        return "Appointment not found", 404

    queue = get_queue_position(patient)

    return render_template(
        "track.html",
        patient=patient,
        token=token,
        position=queue["position"],
        waiting=queue["waiting"],
        estimated_wait=queue["estimated_wait"]
    )


# ---------------- LIVE QUEUE STATUS ----------------

@app.route("/queue-status/<int:token>")
def queue_status(token):

    conn = get_db_connection()

    try:

        patient = conn.execute("""
            SELECT *
            FROM appointments
            WHERE token = ?
        """, (token,)).fetchone()

    finally:

        conn.close()

    if patient is None:

        return {
            "error": "Appointment not found"
        }, 404

    queue = get_queue_position(patient)

    return {
        "token": token,
        "status": patient["status"],
        "position": queue["position"],
        "waiting": queue["waiting"],
        "estimated_wait": queue["estimated_wait"]
    }


# ---------------- ADMIN LOGIN ----------------

@app.route("/login", methods=["GET", "POST"])
def login():

    error = None

    if request.method == "POST":

        username = request.form.get("username", "")

        password = request.form.get("password", "")

        if (
            username == ADMIN_USERNAME
            and password == ADMIN_PASSWORD
        ):

            session["admin_logged_in"] = True

            return redirect(
                url_for("admin_dashboard")
            )

        else:

            error = "Invalid username or password"

    return render_template(
        "login.html",
        error=error
    )


# ---------------- ADMIN LOGOUT ----------------

@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("login"))


# ---------------- ADMIN DASHBOARD ----------------

@app.route("/admin")
@admin_required
def admin_dashboard():

    search = request.args.get(
        "search", ""
    ).strip()

    conn = get_db_connection()

    try:

        if search:

            appointments = conn.execute("""
                SELECT *
                FROM appointments
                WHERE name LIKE ?
                OR department LIKE ?
                OR CAST(token AS TEXT) LIKE ?
                ORDER BY id DESC
            """, (
                f"%{search}%",
                f"%{search}%",
                f"%{search}%"
            )).fetchall()

        else:

            appointments = conn.execute("""
                SELECT *
                FROM appointments
                ORDER BY id DESC
            """).fetchall()

        total = conn.execute("""
            SELECT COUNT(*)
            FROM appointments
        """).fetchone()[0]

        waiting = conn.execute("""
            SELECT COUNT(*)
            FROM appointments
            WHERE status = 'Waiting'
        """).fetchone()[0]

        serving = conn.execute("""
            SELECT COUNT(*)
            FROM appointments
            WHERE status = 'Serving'
        """).fetchone()[0]

        completed = conn.execute("""
            SELECT COUNT(*)
            FROM appointments
            WHERE status = 'Completed'
        """).fetchone()[0]

        cancelled = conn.execute("""
            SELECT COUNT(*)
            FROM appointments
            WHERE status = 'Cancelled'
        """).fetchone()[0]

        departments = conn.execute("""
            SELECT
                department,
                COUNT(*) AS total,
                SUM(
                    CASE WHEN status = 'Waiting'
                    THEN 1 ELSE 0 END
                ) AS waiting
            FROM appointments
            GROUP BY department
        """).fetchall()

    finally:

        conn.close()

    return render_template(
        "admin.html",
        appointments=appointments,
        total=total,
        waiting=waiting,
        serving=serving,
        completed=completed,
        cancelled=cancelled,
        departments=departments,
        search=search
    )


# ---------------- CALL NEXT PATIENT ----------------

@app.route("/call-next")
@admin_required
def call_next():

    conn = get_db_connection()

    try:

        conn.execute("""
            UPDATE appointments
            SET status = 'Completed'
            WHERE status = 'Serving'
        """)

        patient = conn.execute("""
            SELECT id
            FROM appointments
            WHERE status = 'Waiting'
            ORDER BY id ASC
            LIMIT 1
        """).fetchone()

        if patient:

            conn.execute("""
                UPDATE appointments
                SET status = 'Serving'
                WHERE id = ?
            """, (patient["id"],))

        conn.commit()

    finally:

        conn.close()

    return redirect(url_for("admin_dashboard"))


# ---------------- DEPARTMENT-WISE QUEUE ----------------

@app.route("/call-next-department/<department>")
@admin_required
def call_next_department(department):

    conn = get_db_connection()

    try:

        conn.execute("""
            UPDATE appointments
            SET status = 'Completed'
            WHERE department = ?
            AND status = 'Serving'
        """, (department,))

        patient = conn.execute("""
            SELECT id
            FROM appointments
            WHERE department = ?
            AND status = 'Waiting'
            ORDER BY id ASC
            LIMIT 1
        """, (department,)).fetchone()

        if patient:

            conn.execute("""
                UPDATE appointments
                SET status = 'Serving'
                WHERE id = ?
            """, (patient["id"],))

        conn.commit()

    finally:

        conn.close()

    return redirect(url_for("admin_dashboard"))


# ---------------- COMPLETE PATIENT ----------------

@app.route("/complete/<int:patient_id>")
@admin_required
def complete_patient(patient_id):

    conn = get_db_connection()

    try:

        conn.execute("""
            UPDATE appointments
            SET status = 'Completed'
            WHERE id = ?
        """, (patient_id,))

        conn.commit()

    finally:

        conn.close()

    return redirect(url_for("admin_dashboard"))


# ---------------- ADMIN CANCEL APPOINTMENT ----------------

@app.route("/cancel/<int:patient_id>")
@admin_required
def cancel_appointment(patient_id):

    conn = get_db_connection()

    try:

        conn.execute("""
            UPDATE appointments
            SET status = 'Cancelled'
            WHERE id = ?
            AND status = 'Waiting'
        """, (patient_id,))

        conn.commit()

    finally:

        conn.close()

    return redirect(url_for("admin_dashboard"))


# ---------------- PATIENT CANCEL APPOINTMENT ----------------

@app.route("/patient-cancel/<int:token>", methods=["POST"])
def patient_cancel(token):

    conn = get_db_connection()

    try:

        conn.execute("""
            UPDATE appointments
            SET status = 'Cancelled'
            WHERE token = ?
            AND status = 'Waiting'
        """, (token,))

        conn.commit()

    finally:

        conn.close()

    return redirect(
        url_for("track_token", token=token)
    )


# ---------------- EXPORT CSV REPORT ----------------

@app.route("/export-appointments")
@admin_required
def export_appointments():

    conn = get_db_connection()

    try:

        appointments = conn.execute("""
            SELECT
                id,
                name,
                department,
                token,
                status
            FROM appointments
            ORDER BY id DESC
        """).fetchall()

    finally:

        conn.close()

    output = io.StringIO()

    writer = csv.writer(output)

    writer.writerow([
        "ID",
        "Patient Name",
        "Department",
        "OP Token",
        "Status"
    ])

    for patient in appointments:

        writer.writerow([
            patient["id"],
            patient["name"],
            patient["department"],
            patient["token"],
            patient["status"]
        ])

    memory_file = io.BytesIO(
        output.getvalue().encode("utf-8")
    )

    memory_file.seek(0)

    return send_file(
        memory_file,
        mimetype="text/csv",
        as_attachment=True,
        download_name="smartcare_appointments.csv"
    )


# ---------------- RUN APPLICATION ----------------

if __name__ == "__main__":

    app.run(
        host="127.0.0.1",
        port=5001,
        debug=True,
        use_reloader=False
    )
