import os
import uuid
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from db import get_db_connection

app = Flask(__name__, template_folder="Templates", static_folder="Templates")
app.secret_key = "your_secret_key_here"
app.config["UPLOAD_FOLDER"] = os.path.join(app.root_path, "uploads")


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.abspath(os.path.join(BASE_DIR, "..", "uploads"))
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

@app.before_request
def block_raw_dc_html():
    if request.path.endswith(".dc.html"):
        return redirect(url_for("index"))

@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

app = Flask(
    __name__,
    template_folder="Templates/HTML",
    static_folder="Templates",
    static_url_path=""
)
app.secret_key = "ecms_ccis_secret_key"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


# =========================================================
# 1. LANDING, REGISTRATION & AUTHENTICATION
# =========================================================
@app.route("/")
def index():
    return render_template("[1] Landing and Sign-in/(0) Landing page-html/Main.dc.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT user_id, first_name, last_name
        FROM users
        WHERE is_faculty = TRUE
        ORDER BY last_name ASC
    """)
    faculty_list = cursor.fetchall()

    error = None
    created_urec = None
    created_email = None

    if request.method == "POST":
        rep_name = request.form.get("rep_name", "").strip()
        section = request.form.get("section", "").strip().upper()
        group_no = request.form.get("group_no", 1)
        adviser_id = request.form.get("adviser_id") or None
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()

        if "," in rep_name:
            parts = [p.strip() for p in rep_name.split(",", 1)]
            last_name, first_name = parts[0], parts[1]
        elif " " in rep_name:
            parts = rep_name.rsplit(" ", 1)
            first_name, last_name = parts[0], parts[1]
        else:
            first_name, last_name = rep_name, "Student"

        try:
            cursor.execute("SELECT user_id FROM users WHERE email = %s", (email,))
            if cursor.fetchone():
                error = "An account with that email is already registered."
            else:
                new_user_id = f"STU-{uuid.uuid4().hex[:6].upper()}"
                pw_hash = generate_password_hash(password)

                cursor.execute("""
                    INSERT INTO users (user_id, first_name, last_name, email, password_hash, is_student)
                    VALUES (%s, %s, %s, %s, %s, TRUE)
                """, (new_user_id, first_name, last_name, email, pw_hash))

                # Fetch the actual user_id assigned by the MySQL trigger
                cursor.execute("SELECT user_id FROM users WHERE email = %s", (email,))
                actual_user_id = cursor.fetchone()["user_id"]

                cursor.execute("""
                    INSERT INTO submissions (title, section, group_no, submitted_by, adviser_id, status)
                    VALUES (%s, %s, %s, %s, %s, 'Draft')
                """, (f"{section} Group {group_no} Study", section, group_no, actual_user_id, adviser_id))

                cursor.execute("SELECT urec_no FROM submissions WHERE submitted_by = %s LIMIT 1", (actual_user_id,))
                row = cursor.fetchone()
                created_urec = row["urec_no"] if row else "Generated"
                created_email = email
                conn.commit()
        except Exception as err:
            conn.rollback()
            print("REGISTER ERROR:", err)
            error = str(err)

    cursor.close()
    conn.close()

    return render_template(
        "[1] Landing and Sign-in/(5) Register group-html/Register.dc.html",
        faculty_list=faculty_list,
        error=error,
        created_urec=created_urec,
        created_email=created_email
    )


def _verify_and_login(role_key, redirect_endpoint, template_path):
    error = None
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        valid_pw = False
        if user and user.get("password_hash"):
            if user["password_hash"].startswith(("scrypt:", "pbkdf2:")):
                valid_pw = check_password_hash(user["password_hash"], password)
            else:
                valid_pw = (user["password_hash"] == password)

        if not user or not valid_pw:
            error = "Invalid email or password."
        elif not user.get(role_key):
            error = "Your account does not have permission for this portal."
        else:
            session.clear()
            session["user_id"] = user["user_id"]
            session["full_name"] = f"{user['first_name']} {user['last_name']}"
            session["is_student"] = bool(user.get("is_student"))
            session["is_faculty"] = bool(user.get("is_faculty"))
            session["is_evaluator"] = bool(user.get("is_evaluator"))
            session["is_admin"] = bool(user.get("is_admin"))
            return redirect(url_for(redirect_endpoint))

    return render_template(template_path, error=error)


@app.route("/login")
def login_redirect():
    return redirect(url_for("student_login"))


@app.route("/login/student", methods=["GET", "POST"])
def student_login():
    return _verify_and_login(
        "is_student",
        "student_dashboard",
        "[1] Landing and Sign-in/(1) Sign in-html/Login.dc.html"
    )


def _find_login_template(folder_prefix):
    base_dir = os.path.join(app.template_folder, "[1] Landing and Sign-in")
    for folder in os.listdir(base_dir):
        if folder.startswith(folder_prefix):
            folder_path = os.path.join(base_dir, folder)
            if os.path.isdir(folder_path):
                for fname in os.listdir(folder_path):
                    if fname.endswith(".dc.html"):
                        return f"[1] Landing and Sign-in/{folder}/{fname}"
    return "[1] Landing and Sign-in/(1) Sign in-html/Login.dc.html"


@app.route("/login/faculty", methods=["GET", "POST"])
def faculty_login():
    return _verify_and_login(
        "is_faculty",
        "faculty_dashboard",
        _find_login_template("(2)")
    )


@app.route("/login/evaluator", methods=["GET", "POST"])
def evaluator_login():
    return _verify_and_login(
        "is_evaluator",
        "evaluator_dashboard",
        _find_login_template("(3)")
    )


@app.route("/login/admin", methods=["GET", "POST"])
def admin_login():
    return _verify_and_login(
        "is_admin",
        "panel_chair_monitor",
        _find_login_template("(4)")
    )


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

# =========================================================
# 2. STUDENT PORTAL ([2] Students)
# =========================================================
REQUIRED_DOCS = [
    "Form 9",
    "Form 10",
    "Form 11",
    "Form 12",
    "Form 13",
    "Research Instrument",
    "Certification of Validity/Reliability",
    "Curriculum Vitae of the Researchers",
]


@app.route("/student")
def student_dashboard():
    if "user_id" not in session:
        return redirect(url_for("student_login"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT s.*, CONCAT(u.first_name, ' ', u.last_name) AS adviser_name
        FROM submissions s
        LEFT JOIN users u ON s.adviser_id = u.user_id
        WHERE s.submitted_by = %s
        LIMIT 1
    """, (session["user_id"],))
    submission = cursor.fetchone()

    feedback = []
    if submission:
        cursor.execute("SELECT * FROM evals WHERE urec_no = %s", (submission["urec_no"],))
        feedback = cursor.fetchall()

    cursor.close()
    conn.close()
    return render_template(
        "[2] Students/1 Student · My application copy-html/Main-3x08.dc.html",
        submission=submission,
        feedback=feedback
    )


@app.route("/student/documents")
def student_documents():
    if "user_id" not in session:
        return redirect(url_for("student_login"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM users WHERE user_id = %s", (session["user_id"],))
    current_user = cursor.fetchone()

    cursor.execute("SELECT * FROM submissions WHERE submitted_by = %s LIMIT 1", (session["user_id"],))
    submission = cursor.fetchone()

    cursor.execute("SELECT user_id, first_name, last_name FROM users WHERE is_faculty = TRUE")
    advisers = cursor.fetchall()

    uploaded_map = {}
    lead_applicant = None
    co_researchers = []

    if submission:
        cursor.execute("""
            SELECT * FROM files
            WHERE urec_no = %s
            ORDER BY version ASC, uploaded_at ASC
        """, (submission["urec_no"],))
        for f in cursor.fetchall():
            uploaded_map[f["doc_type"]] = f

        cursor.execute("""
            SELECT a.*
            FROM applicants a
            JOIN submissions s ON a.urec_no = s.urec_no
            LEFT JOIN users u ON s.submitted_by = u.user_id
            WHERE a.urec_no = %s
            ORDER BY (a.student_firstName = u.first_name AND a.student_lastName = u.last_name) DESC,
                    a.student_id ASC
        """, (submission["urec_no"],))
        members = cursor.fetchall()

        for m in all_members:
            if (
                current_user
                and m["student_firstName"].lower() == current_user["first_name"].lower()
                and m["student_lastName"].lower() == current_user["last_name"].lower()
                and lead_applicant is None
            ):
                lead_applicant = m
            else:
                co_researchers.append(m)

    cursor.close()
    conn.close()

    template = (
        "[2] Students/2b Student · Submit documents (some uploaded) copy-html/Documents-h6w4.dc.html"
        if uploaded_map else
        "[2] Students/2a Student · Submit documents (nothing uploaded yet) copy-html/DocumentsStart-mz3z.dc.html"
    )
    return render_template(
        template,
        current_user=current_user,
        submission=submission,
        advisers=advisers,
        required_docs=REQUIRED_DOCS,
        uploaded_map=uploaded_map,
        lead_applicant=lead_applicant,
        co_researchers=co_researchers,
        error=request.args.get("error")
    )

@app.route("/student/save-details", methods=["POST"])
def save_student_details():
    if "user_id" not in session:
        return redirect(url_for("student_login"))

    title = request.form.get("title", "").strip()
    section = request.form.get("section", "BSCS 4-1").strip().upper()
    group_no = str(request.form.get("group_no", "1")).strip()
    adviser_id = request.form.get("adviser_id") or None
    lead_student_id = request.form.get("lead_school_id", "").strip()

    if not lead_student_id:
        return redirect(url_for("student_documents", error="Lead researcher Student ID is required."))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT first_name, last_name FROM users WHERE user_id = %s", (session["user_id"],))
        lead_user = cursor.fetchone()

        cursor.execute("SELECT urec_no FROM submissions WHERE submitted_by = %s LIMIT 1", (session["user_id"],))
        existing = cursor.fetchone()

        if existing:
            urec_no = existing["urec_no"]
            cursor.execute("""
                UPDATE submissions
                SET title = %s, section = %s, group_no = %s, adviser_id = %s
                WHERE urec_no = %s
            """, (title, section, group_no, adviser_id, urec_no))
        else:
            cursor.execute("""
                INSERT INTO submissions (title, section, group_no, submitted_by, adviser_id, status)
                VALUES (%s, %s, %s, %s, %s, 'Draft')
            """, (title, section, group_no, session["user_id"], adviser_id))
            cursor.execute("SELECT urec_no FROM submissions WHERE submitted_by = %s LIMIT 1", (session["user_id"],))
            urec_no = cursor.fetchone()["urec_no"]

        # Refresh group members in applicants table using real student numbers
        cursor.execute("DELETE FROM applicants WHERE urec_no = %s", (urec_no,))

        # 1. Insert Lead Researcher
        if lead_user:
            cursor.execute("""
                INSERT INTO applicants (student_id, urec_no, student_firstName, student_lastName, student_school_id, section)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (lead_student_id, urec_no, lead_user["first_name"], lead_user["last_name"], lead_student_id, section))

        # 2. Insert Co-researchers 1 to 3
        # 2. Insert Co-researchers 1 to 3
        for i in range(1, 4):
            full_name = request.form.get(f"co_name_{i}", "").strip()
            co_student_id = request.form.get(f"co_sid_{i}", "").strip()

            if full_name or co_student_id:
                if not (full_name and co_student_id):
                    raise ValueError(f"Co-researcher {i} requires both Full Name and a unique Student ID.")
                if "," in full_name:
                    parts = [p.strip() for p in full_name.split(",", 1)]
                    last_name, first_name = parts[0], parts[1]
                elif " " in full_name:
                    parts = full_name.rsplit(" ", 1)
                    first_name, last_name = parts[0], parts[1]
                else:
                    first_name, last_name = full_name, "-"

                cursor.execute("""
                    INSERT INTO applicants (student_id, urec_no, student_firstName, student_lastName, student_school_id, section)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (co_student_id, urec_no, first_name, last_name, co_student_id, section))

        conn.commit()
    except Exception as err:
        conn.rollback()
        cursor.close()
        conn.close()
        return redirect(url_for("student_documents", error=str(err)))

    cursor.close()
    conn.close()
    return redirect(url_for("student_documents"))


@app.route("/student/upload", methods=["POST"])
def upload_pdf():
    if "user_id" not in session:
        return redirect(url_for("student_login"))

    urec_no = request.form.get("urec_no")
    doc_type = request.form.get("doc_type")
    file = request.files.get("pdf_file")

    if not urec_no:
        return redirect(url_for("student_documents", error="Click 'Save draft' first to generate your UREC number."))
    if not file or file.filename == "":
        return redirect(url_for("student_documents", error="Please select a PDF file."))

    filename = secure_filename(f"{urec_no}_{doc_type}_{file.filename}")
    file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
    file_url = f"/uploads/{filename}"

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Enforces BR-01 and auto-increments file version
        cursor.callproc("upload_submission_file", (urec_no, session["user_id"], doc_type, file_url))
        conn.commit()
    except Exception as err:
        conn.rollback()
        return redirect(url_for("student_documents", error=str(err)))
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for("student_documents"))


@app.route("/student/submit-application", methods=["POST"])
def submit_student_application():
    if "user_id" not in session:
        return redirect(url_for("student_login"))

    urec_no = request.form.get("urec_no")
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE submissions
        SET status = 'Submitted', submitted_at = NOW()
        WHERE urec_no = %s AND submitted_by = %s
    """, (urec_no, session["user_id"]))
    conn.commit()
    cursor.close()
    conn.close()

    return redirect(url_for("student_dashboard"))

# =========================================================
# 3. EVALUATOR PORTAL ([4] Evaluators)
# =========================================================
@app.route("/evaluator")
def evaluator_dashboard():
    if not session.get("is_evaluator"):
        return redirect(url_for("evaluator_login"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT e.eval_id, e.eval_status, e.protocol_comments, e.icf_comments,
               s.urec_no, s.title, s.section, s.group_no, s.status AS submission_status,
               s.submitted_at
        FROM evals e
        JOIN submissions s ON e.urec_no = s.urec_no
        WHERE e.evaluator_id = %s
        ORDER BY e.eval_id DESC
    """, (session["user_id"],))
    assigned = cursor.fetchall()
    cursor.close()
    conn.close()

    incoming_count = sum(1 for p in assigned if p["eval_status"] == "Pending" and not p["protocol_comments"])
    progress_count = sum(1 for p in assigned if p["eval_status"] == "Pending" and p["protocol_comments"])
    completed_count = sum(1 for p in assigned if p["eval_status"] != "Pending")

    return render_template(
        "[4] Evaluators/5 Evaluator · My papers copy-html/Papers-dxay.dc.html",
        assigned=assigned,
        incoming_count=incoming_count,
        progress_count=progress_count,
        completed_count=completed_count
    )


@app.route("/evaluator/studio/<urec_no>")
def evaluator_studio(urec_no):
    if not session.get("is_evaluator"):
        return redirect(url_for("evaluator_login"))

    sheet = request.args.get("sheet", "1")
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT e.*, s.title, s.section, s.group_no, s.submitted_at,
               CONCAT(u.last_name, ', ', u.first_name) AS lead_proponent
        FROM evals e
        JOIN submissions s ON e.urec_no = s.urec_no
        LEFT JOIN users u ON s.submitted_by = u.user_id
        WHERE e.urec_no = %s AND e.evaluator_id = %s
        LIMIT 1
    """, (urec_no, session["user_id"]))
    evaluation = cursor.fetchone()

    if not evaluation:
        cursor.close()
        conn.close()
        return redirect(url_for("evaluator_dashboard"))

    # Get latest version of each uploaded document
    cursor.execute("""
        SELECT f.*
        FROM files f
        INNER JOIN (
            SELECT doc_type, MAX(version) AS max_ver
            FROM files
            WHERE urec_no = %s
            GROUP BY doc_type
        ) latest ON f.doc_type = latest.doc_type AND f.version = latest.max_ver
        WHERE f.urec_no = %s
        ORDER BY f.file_id ASC
    """, (urec_no, urec_no))
    files = cursor.fetchall()
    cursor.close()
    conn.close()

    active_file = files[0] if files else None
    if sheet == "2" and files:
        for f in files:
            if "consent" in f["doc_type"].lower() or "form 13" in f["doc_type"].lower():
                active_file = f
                break

    template = (
        "[4] Evaluators/6e Evaluator · Studio, sheet 2 of 2 (full details) copy-html/StudioConsent-n47h.dc.html"
        if sheet == "2" else
        "[4] Evaluators/6c Evaluator · Studio, sheet 1 of 2 (full details) copy-html/Studio-ih66.dc.html"
    )
    return render_template(
        template,
        evaluation=evaluation,
        files=files,
        active_file=active_file,
        saved=request.args.get("saved")
    )


@app.route("/evaluator/save-sheet1/<int:eval_id>", methods=["POST"])
def save_evaluator_sheet1(eval_id):
    if not session.get("is_evaluator"):
        return redirect(url_for("evaluator_login"))

    urec_no = request.form.get("urec_no")
    rec_label = request.form.get("sheet1_rec", "").strip()
    concerns = request.form.get("other_concerns", "").strip()
    remarks = request.form.get("remarks", "").strip()
    action = request.form.get("action", "save")

    parts = []
    if rec_label:
        parts.append(f"[Protocol Sheet: {rec_label}]")
    if concerns:
        parts.append(concerns)
    if remarks:
        parts.append(remarks)
    protocol_comments = " ".join(parts) if parts else "Protocol review in progress."

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE evals
        SET protocol_comments = %s
        WHERE eval_id = %s AND evaluator_id = %s
    """, (protocol_comments, eval_id, session["user_id"]))
    conn.commit()
    cursor.close()
    conn.close()

    if action == "next":
        return redirect(url_for("evaluator_studio", urec_no=urec_no, sheet="2"))
    return redirect(url_for("evaluator_studio", urec_no=urec_no, sheet="1", saved="1"))


@app.route("/evaluator/submit/<int:eval_id>", methods=["POST"])
def submit_evaluation(eval_id):
    if not session.get("is_evaluator"):
        return redirect(url_for("evaluator_login"))

    rec_label = request.form.get("sheet2_rec", "Approved").strip()
    concerns = request.form.get("other_concerns", "").strip()
    remarks = request.form.get("remarks", "").strip()

    # Map UI recommendation label to database eval_status ('Approved' or 'For Revision')
    db_status = "Approved" if rec_label in ("Approved", "Exempt from review") else "For Revision"

    parts = [f"[ICF Sheet: {rec_label}]"]
    if concerns:
        parts.append(concerns)
    if remarks:
        parts.append(remarks)
    icf_comments = " ".join(parts)

    conn = get_db_connection()
    cursor = conn.cursor()
    # Automatically fires after_eval_update trigger (BR-04 consensus / BR-05 stalemate)
    cursor.execute("""
        UPDATE evals
        SET eval_status = %s, icf_comments = %s
        WHERE eval_id = %s AND evaluator_id = %s
    """, (db_status, icf_comments, eval_id, session["user_id"]))
    conn.commit()
    cursor.close()
    conn.close()

    return redirect(url_for("evaluator_dashboard"))

# =========================================================
# 4. PANEL CHAIR & TECH ASSIST ([6] IF Tech Assist and Panel Chair...)
# =========================================================
@app.route("/panel-chair")
@app.route("/panel-chair/monitor")
def panel_chair_monitor():
    if not session.get("is_admin"):
        return redirect(url_for("admin_login"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM vw_chair_dashboard ORDER BY submitted_at DESC")
    submissions = cursor.fetchall()
    cursor.close()
    conn.close()

    total_count = len(submissions)
    under_review_count = sum(1 for s in submissions if s["verdict_status"] in ("Under Review", "Stalemate - For Panel Chair Review"))
    cleared_count = sum(1 for s in submissions if s["verdict_status"] == "Cleared")
    bscs_count = sum(1 for s in submissions if (s["program"] or "").upper() == "BSCS")
    bsit_count = sum(1 for s in submissions if (s["program"] or "").upper() == "BSIT")

    bscs_pct = int((bscs_count / total_count) * 100) if total_count else 0
    bsit_pct = int((bsit_count / total_count) * 100) if total_count else 0

    return render_template(
        "[6] IF Tech Assist and Panel Chair SHARE the same screen/(1) Monitor copy-html/Monitor-jz46.dc.html",
        submissions=submissions,
        total_count=total_count,
        under_review_count=under_review_count,
        cleared_count=cleared_count,
        bscs_count=bscs_count,
        bsit_count=bsit_count,
        bscs_pct=bscs_pct,
        bsit_pct=bsit_pct
    )


@app.route("/panel-chair/decisions")
def panel_chair_decisions():
    if not session.get("is_admin"):
        return redirect(url_for("admin_login"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # 1. Split verdicts (BR-05 Stalemates)
    cursor.execute("""
        SELECT s.urec_no, s.title, s.section, s.status
        FROM submissions s
        WHERE s.status = 'Stalemate - For Panel Chair Review'
    """)
    stalemates = cursor.fetchall()
    for st in stalemates:
        cursor.execute("""
            SELECT e.eval_status, e.protocol_comments, e.icf_comments,
                   CONCAT(u.first_name, ' ', u.last_name) AS evaluator_name
            FROM evals e
            JOIN users u ON e.evaluator_id = u.user_id
            WHERE e.urec_no = %s
            ORDER BY e.eval_id ASC
        """, (st["urec_no"],))
        st["eval_list"] = cursor.fetchall()

    # 2. Cleared submissions ready for certificate issuance
    cursor.execute("""
        SELECT s.urec_no, s.title, s.section, s.group_no,
               CONCAT(u.first_name, ' ', u.last_name) AS lead_proponent
        FROM submissions s
        LEFT JOIN users u ON s.submitted_by = u.user_id
        WHERE s.status = 'Cleared'
        ORDER BY s.submitted_at DESC
    """)
    cleared_list = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "[6] IF Tech Assist and Panel Chair SHARE the same screen/(2) Approvals copy-html/Decisions-8pt9.dc.html",
        stalemates=stalemates,
        cleared_list=cleared_list,
        msg=request.args.get("msg")
    )


@app.route("/panel-chair/resolve-stalemate", methods=["POST"])
def resolve_stalemate():
    if not session.get("is_admin"):
        return redirect(url_for("admin_login"))

    urec_no = request.form.get("urec_no")
    decision = request.form.get("decision")  # 'Cleared' or 'For Revision'

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE submissions SET status = %s WHERE urec_no = %s", (decision, urec_no))
    conn.commit()
    cursor.close()
    conn.close()

    return redirect(url_for("panel_chair_decisions", msg=f"{urec_no} updated to {decision}."))


@app.route("/panel-chair/screening", methods=["GET", "POST"])
def panel_chair_screening():
    if not session.get("is_admin"):
        return redirect(url_for("admin_login"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == "POST":
        urec_no = request.form.get("urec_no")
        passed = request.form.get("passed") == "1"
        remarks = request.form.get("remarks", "").strip()
        cursor.callproc("screen_submission", (urec_no, passed, remarks))
        conn.commit()

    # Fetch submissions waiting for or currently in screening
    cursor.execute("""
        SELECT s.urec_no, s.title, s.section, s.status, s.screening_remarks, s.submitted_at,
               (SELECT COUNT(DISTINCT doc_type) FROM files f WHERE f.urec_no = s.urec_no) AS doc_count
        FROM submissions s
        WHERE s.status IN ('Submitted', 'Returned - Incomplete', 'Draft')
        ORDER BY s.submitted_at ASC
    """)
    queue = cursor.fetchall()

    selected_urec = request.args.get("urec_no") or (queue[0]["urec_no"] if queue else None)
    selected_sub = None
    uploaded_docs = {}

    if selected_urec:
        cursor.execute("SELECT * FROM submissions WHERE urec_no = %s", (selected_urec,))
        selected_sub = cursor.fetchone()
        cursor.execute("""
            SELECT doc_type, file_url, MAX(version) AS version
            FROM files
            WHERE urec_no = %s
            GROUP BY doc_type, file_url
        """, (selected_urec,))
        for f in cursor.fetchall():
            uploaded_docs[f["doc_type"]] = f

    cursor.close()
    conn.close()

    return render_template(
        "[6] IF Tech Assist and Panel Chair SHARE the same screen/(3) Screening copy-html/Screening-qr8z-uqay.dc.html",
        queue=queue,
        selected_sub=selected_sub,
        required_docs=REQUIRED_DOCS,
        uploaded_docs=uploaded_docs
    )


@app.route("/panel-chair/assign", methods=["GET", "POST"])
def panel_chair_assign():
    if not session.get("is_admin"):
        return redirect(url_for("admin_login"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    error = None
    success = None

    if request.method == "POST":
        urec_no = request.form.get("urec_no")
        eval_1 = request.form.get("evaluator_1")
        eval_2 = request.form.get("evaluator_2")

        if not urec_no or not eval_1 or not eval_2:
            error = "Please select an application and two evaluators."
        elif eval_1 == eval_2:
            error = "Evaluator 1 and Evaluator 2 must be two different people."
        else:
            try:
                # Triggers enforce BR-02 (2-cap), BR-03 (COI), and BR-06 (Screened first)
                cursor.execute("INSERT INTO evals (urec_no, evaluator_id) VALUES (%s, %s)", (urec_no, eval_1))
                cursor.execute("INSERT INTO evals (urec_no, evaluator_id) VALUES (%s, %s)", (urec_no, eval_2))
                conn.commit()
                success = f"Assigned both evaluators to {urec_no}. Status moved to Under Review."
            except Exception as err:
                conn.rollback()
                error = str(err)

    cursor.execute("""
        SELECT s.urec_no, s.title, s.section, s.adviser_id, s.status
        FROM submissions s
        WHERE s.status != 'Cleared'
        ORDER BY (s.status = 'Ready for Evaluation') DESC, s.submitted_at DESC
    """)
    submissions = cursor.fetchall()

    cursor.execute("""
        SELECT u.user_id, u.first_name, u.last_name,
               (SELECT COUNT(*) FROM evals e WHERE e.evaluator_id = u.user_id AND e.eval_status = 'Pending') AS active_papers
        FROM users u
        WHERE u.is_evaluator = TRUE
        ORDER BY active_papers ASC, u.last_name ASC
    """)
    evaluators = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "[6] IF Tech Assist and Panel Chair SHARE the same screen/(4) Assign evaluators copy-html/Assign-w2mb-dgk8.dc.html",
        submissions=submissions,
        evaluators=evaluators,
        error=error,
        success=success
    )

# =========================================================
# 5. FACULTY ADVISER PORTAL ([7] Faculty Adviser Screen)
# =========================================================
@app.route("/faculty")
def faculty_dashboard():
    if not session.get("is_faculty"):
        return redirect(url_for("faculty_login"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT s.urec_no, s.title, s.section, s.group_no, s.status, s.submitted_at,
               CONCAT(u.first_name, ' ', u.last_name) AS lead_researcher
        FROM submissions s
        LEFT JOIN users u ON s.submitted_by = u.user_id
        WHERE s.adviser_id = %s
        ORDER BY s.group_no ASC, s.submitted_at DESC
    """, (session["user_id"],))
    advisees = cursor.fetchall()

    # Attach latest uploaded PDFs per group for read-only viewing
    for group in advisees:
        cursor.execute("""
            SELECT f.doc_type, f.file_url, f.version
            FROM files f
            INNER JOIN (
                SELECT doc_type, MAX(version) AS max_ver
                FROM files
                WHERE urec_no = %s
                GROUP BY doc_type
            ) latest ON f.doc_type = latest.doc_type AND f.version = latest.max_ver
            WHERE f.urec_no = %s
            ORDER BY f.file_id ASC
        """, (group["urec_no"], group["urec_no"]))
        group["files"] = cursor.fetchall()

    cursor.close()
    conn.close()

    total_groups = len(advisees)
    under_review = sum(1 for g in advisees if g["status"] in ("Under Review", "Ready for Evaluation", "Stalemate - For Panel Chair Review"))
    approved = sum(1 for g in advisees if g["status"] == "Cleared")
    for_revision = sum(1 for g in advisees if g["status"] in ("For Revision", "Returned - Incomplete"))
    sections = sorted({g["section"] for g in advisees if g["section"]})
    section_label = ", ".join(sections) if sections else "Assigned Sections"

    return render_template(
        "[7] Faculty Adviser Screen (Read-Only)/My Advisees (Read-Only) copy-html/Faculty-c4n6.dc.html",
        advisees=advisees,
        total_groups=total_groups,
        under_review=under_review,
        approved=approved,
        for_revision=for_revision,
        section_label=section_label
    )


if __name__ == "__main__":
    app.run(debug=True)