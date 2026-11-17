import os
from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory
from werkzeug.utils import secure_filename
from db import get_db_connection

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.abspath(os.path.join(BASE_DIR, "..", "uploads"))
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(
    __name__,
    template_folder="Templates/HTML",
    static_folder="Templates",
    static_url_path=""
)
app.secret_key = "ecms_ccis_secret_key"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


# =========================================================
# 1. SIGN-IN PAGES ([1] Landing and Sign-in)
# =========================================================
@app.route("/")
@app.route("/login/student", methods=["GET", "POST"])
def student_login():
    # Update filename inside (1) Sign in-html if named differently
    return handle_login("[1] Landing and Sign-in/(1) Sign in-html/index.html", "student_dashboard")

@app.route("/login/faculty", methods=["GET", "POST"])
def faculty_login():
    return handle_login("[1] Landing and Sign-in/(2) Faculty Adviser sign in-html/index.html", "fic_dashboard")

@app.route("/login/evaluator", methods=["GET", "POST"])
def evaluator_login():
    return handle_login("[1] Landing and Sign-in/(3) Evaluator sign in-html/index.html", "evaluator_dashboard")

@app.route("/login/admin", methods=["GET", "POST"])
def admin_login():
    return handle_login("[1] Landing and Sign-in/(4) Admin sign in-html/Admin-Login.dc.html", "panel_chair_dashboard")


def handle_login(template_path, target_route):
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user and user["password_hash"] == password:
            session["user_id"] = user["user_id"]
            session["full_name"] = f"{user['first_name']} {user['last_name']}"
            session["is_admin"] = bool(user["is_admin"])
            session["is_evaluator"] = bool(user["is_evaluator"])
            session["is_faculty"] = bool(user["is_faculty"])
            session["is_student"] = bool(user["is_student"])
            return redirect(url_for(target_route))

        return render_template(template_path, error="Invalid email or password.")

    return render_template(template_path)


# =========================================================
# 2. ROLE DASHBOARDS (Point each route to its .dc.html file)
# =========================================================
@app.route("/student")
def student_dashboard():
    # Replace 'Student-Application.dc.html' with the exact .dc.html filename inside [2] Students/1 Student...
    return render_template("[2] Students/1 Student · My application copy-html/Student-Application.dc.html")

@app.route("/evaluator")
def evaluator_dashboard():
    # Point to the .dc.html file inside [4] Evaluators
    return render_template("[4] Evaluators/Evaluator.dc.html")

@app.route("/panel-chair")
def panel_chair_dashboard():
    # Point to the .dc.html file inside [6] IF Tech Assist and Panel Chair...
    return render_template("[6] IF Tech Assist and Panel Chair SHA-html/Panel-Chair.dc.html")

@app.route("/fic")
def fic_dashboard():
    # Point to the .dc.html file inside [7] Faculty Adviser Screen...
    return render_template("[7] Faculty Adviser Screen (Read-Only)-html/FIC-Dashboard.dc.html")

@app.route("/uploads/<path:filename>")
def serve_pdf(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)


if __name__ == "__main__":
    app.run(debug=True)