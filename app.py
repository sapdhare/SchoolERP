from flask import Flask, render_template, session, request, redirect, url_for, send_file, jsonify
import pdfkit
import pandas as pd
import os
import subprocess
import random
import re
import smtplib
import razorpay

from flask_wtf.csrf import CSRFProtect
 

from flask_bcrypt import Bcrypt
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash

from email.mime.text import MIMEText
from email.header import Header
from email.mime.multipart import MIMEMultipart


from datetime import datetime, date, timedelta
from functools import wraps

from apscheduler.schedulers.background import BackgroundScheduler

from flask_mail import Mail, Message
from db import get_connection

from dotenv import load_dotenv


# Load env variables from .env file

load_dotenv()

# Initialize Flask app
app = Flask(__name__)

 

# Secret key for sessions 
app.secret_key = os.getenv("SECRET_KEY")

# Enable CSRF protection
csrf = CSRFProtect(app)

# =========================================================
# PDF CONFIGURATION
# =========================================================

WKHTMLTOPDF_PATH = r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe"

pdf_config = pdfkit.configuration(
    wkhtmltopdf=WKHTMLTOPDF_PATH
)

# =========================================================
# SESSION SECURITY CONFIGURATION
# =========================================================

# Prevent JavaScript access to cookies
app.config["SESSION_COOKIE_HTTPONLY"] = True

# Use True in production with HTTPS
app.config["SESSION_COOKIE_SECURE"] = False #LAter make it True

# Protect against CSRF-like cross-site behavior
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

# Session auto-expiry
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(minutes=30)



# Initialize Bcrypt for password hashing
bcrypt = Bcrypt(app)


# =========================================================
# MAIL CONFIGURATION
# =========================================================

app.config["MAIL_SERVER"] = "smtp.gmail.com"
app.config["MAIL_PORT"] = 587
app.config["MAIL_USE_TLS"] = True
app.config["MAIL_USE_SSL"] = False

# your gmail
app.config["MAIL_USERNAME"] = os.getenv("MAIL_USERNAME")

# gmail app password (not normal password)
app.config["MAIL_PASSWORD"] = os.getenv("MAIL_PASSWORD")

app.config["MAIL_DEFAULT_SENDER"] = os.getenv("MAIL_USERNAME")

# initialize mail
mail = Mail(app)

# Razorpay Configuration

RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")

if not RAZORPAY_KEY_ID or not RAZORPAY_KEY_SECRET:
    raise Exception("Razorpay keys missing in .env")
 

# =========================================================
# 🛠️ COMMON HELPER FUNCTIONS (USED ACROSS APP)
# =========================================================


# =========================================================
# 🌍 GLOBAL ERP SETTINGS
# =========================================================

@app.context_processor
def inject_system_settings():

    conn = None
    cursor = None

    try:

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT TOP 1
                system_name,
                system_logo,
                support_email,
                support_phone
            FROM system_settings
        """)

        row = cursor.fetchone()

        if row:

            return {
                "global_settings": {
                    "system_name": row[0],
                    "system_logo": row[1],
                    "support_email": row[2],
                    "support_phone": row[3]
                }
            }

    except Exception as e:

        print("GLOBAL SETTINGS ERROR:", e)

    finally:

        if cursor:
            cursor.close()

        if conn:
            conn.close()

    return {
        "global_settings": {}
    }

# =========================================================
# 📧 GLOBAL EMAIL SENDER
# =========================================================

def send_email(

    to_email,
    subject,
    body,
    attachment_path=None,
    attachment_name=None

):

    conn = None
    cursor = None
    server = None

    try:

        # =========================================
        # DB CONNECTION
        # =========================================

        conn = get_connection()
        cursor = conn.cursor()

        # =========================================
        # GET SMTP SETTINGS
        # =========================================

        cursor.execute("""

            SELECT

                smtp_email,
                smtp_password,
                smtp_server,
                smtp_port,
                smtp_tls

            FROM system_settings
            WHERE id = 1

        """)

        smtp = cursor.fetchone()

        if not smtp:
            return False

        smtp_email = smtp[0]
        smtp_password = smtp[1]
        smtp_server = smtp[2]
        smtp_port = int(smtp[3])
        smtp_tls = smtp[4]

        # =========================================
        # CREATE EMAIL
        # =========================================

        message = MIMEMultipart()

        message["From"] = smtp_email
        message["To"] = to_email

        message["Subject"] = Header(
            subject,
            "utf-8"
        )

        # =========================================
        # EMAIL BODY
        # =========================================

        message.attach(

            MIMEText(
                body,
                "html",
                "utf-8"
            )

        )

        # =========================================
        # PDF ATTACHMENT
        # =========================================

        if attachment_path and attachment_name:

            from email.mime.base import MIMEBase
            from email import encoders

            with open(attachment_path, "rb") as file:

                part = MIMEBase(
                    "application",
                    "octet-stream"
                )

                part.set_payload(
                    file.read()
                )

            encoders.encode_base64(part)

            part.add_header(

                "Content-Disposition",

                f'attachment; filename="{attachment_name}"'

            )

            message.attach(part)

        # =========================================
        # SMTP CONNECTION
        # =========================================

        server = smtplib.SMTP(

            smtp_server,
            smtp_port

        )

        # =========================================
        # TLS SECURITY
        # =========================================

        if str(smtp_tls).strip() == "Enabled":

            server.starttls()

        # =========================================
        # LOGIN
        # =========================================

        server.login(

            smtp_email,
            smtp_password

        )

        # =========================================
        # SEND EMAIL
        # =========================================

        server.sendmail(

            smtp_email,
            to_email,
            message.as_bytes()

        )

        print("✅ EMAIL SENT")

        return True

    except Exception as e:

        print(
            "❌ EMAIL SEND ERROR:",
            str(e)
        )

        return str(e)

    finally:

        # =========================================
        # CLOSE SMTP
        # =========================================

        try:
            if server:
                server.quit()
        except:
            pass

        # =========================================
        # CLOSE DB
        # =========================================

        if cursor:
            cursor.close()

        if conn:
            conn.close()
           
 
# =========================================================
# 🛠 GLOBAL MAINTENANCE CHECK
# =========================================================

@app.before_request
def check_maintenance_mode():

    try:

        # =========================================
        # ALLOW STATIC FILES
        # =========================================

        if request.path.startswith("/static"):
            return

        # =========================================
        # ALLOW ADMIN ACCESS
        # =========================================

        if session.get("admin_role") == "admin":
            return

        # =========================================
        # DB CONNECTION
        # =========================================

        conn = get_connection()
        cursor = conn.cursor()

        # =========================================
        # GET MAINTENANCE STATUS
        # =========================================

        cursor.execute("""

            SELECT

                maintenance_mode,
                maintenance_message

            FROM system_settings

            WHERE id = 1

        """)

        row = cursor.fetchone()

        cursor.close()
        conn.close()

        if not row:
            return

        maintenance_mode = row[0]
        maintenance_message = row[1]

        # =========================================
        # BLOCK USERS
        # =========================================

        if maintenance_mode == "ON":

            return render_template(

                "maintenance.html",

                message=maintenance_message

            )

    except Exception as e:

        print(
            "❌ MAINTENANCE CHECK ERROR:",
            e
        )


# =========================================================
# 🌟 GLOBAL BRANDING FUNCTION
# =========================================================

        # @app.context_processor
        # def inject_branding_settings():

        #     conn = get_connection()
        #     cursor = conn.cursor()

        #     try:

        #         cursor.execute("""
        #             SELECT
        #                 primary_color,
        #                 secondary_color,
        #                 button_color,
        #                 system_logo,
        #                 favicon,
        #                 system_name,
        #                 footer_text,
        #                 erp_version
        #             FROM system_settings
        #             WHERE id = 1
        #         """)

        #         branding = cursor.fetchone()

        #         return dict(
        #             global_settings=branding
        #         )

        #     except Exception as e:

        #         print("Branding Context Error:", e)

        #         return dict(
        #             global_settings=None
        #         )

        #     finally:

        #         cursor.close()
        #         conn.close()

# =========================================================
# 🌟 SCHOOL SPECIFIC FEATURE MODULES
# =========================================================

@app.context_processor
def inject_feature_modules():

    conn = None
    cursor = None

    try:

        # =========================================
        # GET CURRENT CLERK SCHOOL
        # =========================================

        school_id = session.get(
            "clerk_school_id"
        )

        # =========================================
        # IF NOT CLERK LOGIN
        # =========================================

        if not school_id:

            return {
                "feature_modules": {}
            }

        conn = get_connection()
        cursor = conn.cursor()

        # =========================================
        # GET SCHOOL FEATURES
        # =========================================

        cursor.execute("""
            SELECT

                enable_tc_management,
                enable_bonafide_management,

                enable_import_export,
                enable_attendance,
                enable_fee_management,
                enable_teacher_management,
                enable_results,
                enable_timetable,
                enable_notice_board

            FROM schools
            WHERE school_id = ?
        """, (school_id,))

        row = cursor.fetchone()

        # =========================================
        # NO SCHOOL FOUND
        # =========================================

        if not row:

            return {
                "feature_modules": {}
            }

        # =========================================
        # RETURN FEATURES
        # =========================================

        return {

            "feature_modules": {

                "tc": row[0],
                "bonafide": row[1],

                "import_export": row[2],
                "attendance": row[3],
                "fees": row[4],
                "teachers": row[5],
                "results": row[6],
                "timetable": row[7],
                "notice_board": row[8]

            }

        }

    except Exception as e:

        print(
            "FEATURE MODULE ERROR:",
            e
        )

        return {
            "feature_modules": {}
        }

    finally:

        if cursor:
            cursor.close()

        if conn:
            conn.close()


# =========================================================
# GET SCHOOL DETAILS (GLOBAL FIX)
# =========================================================
def get_school_details(school_id):

    conn = None
    cursor = None

    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                school_id,
                name,
                udise_no
            FROM schools
            WHERE school_id = ?
        """, (school_id,))

        school = cursor.fetchone()

        if not school:
            return None

        return {
            "school_id": school.school_id,
            "school_name": school.name,
            "school_udise": school.udise_no
        }

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


# ---------------------------------------------------------
# 🔹 HANDLE NULL / EMPTY VALUES (MAINLY FOR EXCEL IMPORT)
# ---------------------------------------------------------
def safe_value(val):
    """
    Converts Excel/DB value safely:
    - If NaN → returns None
    - Else → returns cleaned string
    """
    import pandas as pd

    if pd.isna(val):
        return None

    return str(val).strip()

# ---------------------------------------------------------
# 🔹 VALIDATION HELPER 
#---------------------------------------------------------

def is_valid_email(email):
    pattern = r"^[^\s@]+@[^\s@]+\.[^\s@]+$"
    return re.match(pattern, email)


def is_valid_phone(phone):
    return phone.isdigit() and len(phone) == 10


def is_valid_aadhaar(aadhaar):
    return aadhaar.isdigit() and len(aadhaar) == 12


# ---------------------------------------------------------
# 🔹 HANDLE DATE FROM EXCEL (IMPORT SIDE)
# ---------------------------------------------------------
def safe_date(val):
    """
    Converts Excel date to DB format (YYYY-MM-DD)

    Example:
    Excel → 2008-09-23 → '2008-09-23'

    Returns:
    - Proper string date OR
    - None if invalid
    """
    import pandas as pd

    if pd.isna(val):
        return None

    try:
        return pd.to_datetime(val).strftime("%Y-%m-%d")
    except Exception:
        return None


# ---------------------------------------------------------
# 🔹 GET SCHOOL CODE (USED IN ID GENERATION)
# ---------------------------------------------------------
def get_school_code(school_id):
    """
    Fetch school_code from DB

    Used in:
    - Admission No → ABC-ADM-0001
    - TC No        → ABC-TC-0001
    - Bonafide No  → ABC-BON-0001
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT school_code 
        FROM schools 
        WHERE school_id = ?
    """, (school_id,))

    row = cursor.fetchone()

    cursor.close()
    conn.close()

    return row[0] if row else "SCH"   # fallback



# ---------------------------------------------------------
# 🔹 PARSE FORM DATE → PYTHON DATE (FORM INPUT)
# ---------------------------------------------------------
def parse_date(date_str):
    """
    Converts form string → datetime object

    Example:
    '2026-04-17' → datetime object
    '17-04-2026' → datetime object

    Used in:
    - Add Student
    - TC Form
    - Bonafide Form
    """
    from datetime import datetime

    if not date_str:
        return None

    try:
        # FORMAT: YYYY-MM-DD
        return datetime.strptime(
            date_str,
            "%Y-%m-%d"
        )

    except Exception:
        try:
            # FORMAT: DD-MM-YYYY
            return datetime.strptime(
                date_str,
                "%d-%m-%Y"
            )

        except Exception:
            return None


# ---------------------------------------------------------
# 🔹 FORMAT DATE FOR UI / PDF DISPLAY
# ---------------------------------------------------------
def format_date(d):
    """
    Converts DB date → readable format

    Example:
    2026-04-17 → 17-04-2026

    Used in:
    - TC view
    - Bonafide view
    - Print / PDF
    """
    if not d:
        return ""

    try:
        return d.strftime("%d-%m-%Y")
    except Exception:
        return str(d)
    
# ---------------------------------------------------------
# ADMIN PROTECTION
# ---------------------------------------------------------
    
def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("admin_logged_in") or session.get("admin_role") != "admin":
            return "Unauthorized ❌"
        return f(*args, **kwargs)
    return wrapper

# ---------------------------------------------------------
# LOGIN PROTECTION (BOTH CLERK + ADMIN)
# ---------------------------------------------------------
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):

        clerk_logged_in = session.get("clerk_logged_in")
        clerk_role = session.get("clerk_role")

        admin_logged_in = session.get("admin_logged_in")
        admin_role = session.get("admin_role")

        clerk_ok = (
            clerk_logged_in is True
            and clerk_role == "clerk"
        )

        admin_ok = (
            admin_logged_in is True
            and admin_role == "admin"
        )

        if not clerk_ok and not admin_ok:
            return redirect(url_for("login"))

        return f(*args, **kwargs)

    return decorated_function

# =========================================================
# 🛡 SCHOOL FEATURE ACCESS CHECK
# PURPOSE:
# Check module access school-wise
# Supports SaaS + subscription based ERP
# =========================================================

def is_module_enabled(module_name):

    conn = None
    cursor = None

    try:

        # =========================================
        # GET CURRENT SCHOOL
        # =========================================

        school_id = session.get(
            "clerk_school_id"
        )

        if not school_id:
            return False

        # =========================================
        # ALLOWED MODULES (SECURITY)
        # =========================================

        allowed_modules = [

            "enable_tc_management",
            "enable_bonafide_management",

            "enable_import_export",
            "enable_attendance",
            "enable_fee_management",
            "enable_teacher_management",
            "enable_results",
            "enable_timetable",
            "enable_notice_board"
        ]

        # SECURITY BLOCK
        if module_name not in allowed_modules:
            return False

        # =========================================
        # DB CONNECTION
        # =========================================

        conn = get_connection()
        cursor = conn.cursor()

        # =========================================
        # SCHOOL SPECIFIC CHECK
        # =========================================

        query = f"""
            SELECT {module_name}
            FROM schools
            WHERE school_id = ?
        """

        cursor.execute(
            query,
            (school_id,)
        )

        row = cursor.fetchone()

        # =========================================
        # ENABLED CHECK
        # =========================================

        if row and str(row[0]).strip() == "Enabled":
            return True

        return False

    except Exception as e:

        print(
            "❌ MODULE CHECK ERROR:",
            e
        )

        return False

    finally:

        if cursor:
            cursor.close()

        if conn:
            conn.close()

# ---------------------------------------------------------
# 🔹 CREATE SUBSCRIPTION (USED IN SCHOOL CREATION + RENEWAL)
# ---------------------------------------------------------

def create_subscription(school_id, plan_name, days, amount):
    conn = get_connection()
    cursor = conn.cursor()

    start_date = date.today()
    end_date = start_date + timedelta(days=days)

    cursor.execute("""
        INSERT INTO subscriptions
        (
            school_id,
            plan_name,
            start_date,
            end_date,
            status,
            amount
        )
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        school_id,
        plan_name,
        start_date,
        end_date,
        "active",
        amount
    ))

    conn.commit()



 # =========================================================
# 📧 TEST SMTP EMAIL
# =========================================================
@app.route(
    "/superadmin/test-email"
)
@admin_required
def test_email():

    try:

        # =========================================
        # TEST RECEIVER EMAIL
        # =========================================

        test_receiver = "swarajdhaskat02@gmail.com"

        # =========================================
        # EMAIL SUBJECT
        # =========================================

        subject = (
            "ShalaSync ERP SMTP Test "
        )

        # =========================================
        # EMAIL BODY
        # =========================================

        body = """

        <div style="font-family:Arial;padding:20px;">

            <h2 style="color:#10b981;">
                SMTP Test Successful 
            </h2>

            <p>
                Your ERP email engine is
                working correctly.
            </p>

            <hr>

            <p>
                <b>System:</b>
                ShalaSync ERP
            </p>

            <p>
                <b>Status:</b>
                Email Delivery Active
            </p>

        </div>

        """

        # =========================================
        # SEND EMAIL
        # =========================================

        success = send_email(

            test_receiver,
            subject,
            body

        )

        # =========================================
        # RESULT
        # =========================================

        if success == True:

            return """

            <h2>
                 Test Email Sent Successfully
            </h2>

            """

        else:

            return """

            <h2>
                 {success}
            </h2>

            """

    except Exception as e:

        print(
            "TEST EMAIL ERROR:",
            e
        )

        return f"""

        <h2>
             SMTP Test Failed
        </h2>

        <p>{e}</p>

        """

# =========================================================
# 🏠 HOME ROUTE
# =========================================================
@app.route('/')
def home():
    return render_template('index.html')
 

# =========================================================
# 🔐 CLERK LOGIN (DB BASED)
# =========================================================
@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()

        # ================= EMPTY INPUT VALIDATION =================
        if not email or not password:
            return "Email and password required ❌"
        
        if not is_valid_email(email):
            return "Invalid email format ❌"

         # LOGIN RATE LIMIT

        failed_attempts = session.get("clerk_failed_attempts", 0)

        if failed_attempts >= 5:
            return "Too many failed login attempts. Try again later ❌"


        conn = None
        cursor = None

        try:
            conn = get_connection()
            cursor = conn.cursor()

            # USERS + SCHOOL JOIN
            cursor.execute("""
                SELECT 
                    u.id,
                    u.email,
                    u.password,
                    u.school_id,
                    u.status,
                    s.name,
                    s.is_active
                FROM users u
                JOIN schools s
                ON u.school_id = s.school_id
                WHERE u.email = ?
                AND u.role = 'clerk'
            """, (email,))

            user = cursor.fetchone()

          
            # ================= USER EXISTS =================
            if user:

                db_password = user[2]
                user_status = user[4]
                school_status = user[6]
              
            # ================= HASH PASSWORD CHECK =================
                if bcrypt.check_password_hash(
                    db_password,
                    password
                ):

                    # SCHOOL ACTIVE CHECK
                    if school_status == 0:
                        return "School access deactivated by admin ❌"

                    # ACCOUNT ACTIVE CHECK
                    if user_status != "active":
                        return "Your account is inactive. Please renew subscription ❌"

                    # UPDATE LAST LOGIN
                    cursor.execute("""
                        UPDATE users
                        SET 
                            last_login = GETDATE(),
                            updated_at = GETDATE()
                        WHERE id = ?
                    """, (user[0],))

                    conn.commit()

                    
                    

                    # clear old clerk session
                    session.pop("clerk_logged_in", None)
                    session.pop("clerk_user_id", None)
                    session.pop("clerk_email", None)
                    session.pop("clerk_school_id", None)
                    session.pop("clerk_role", None)

                    # create clerk session
                    session.pop("clerk_failed_attempts", None)

                    session["clerk_logged_in"] = True
                    session["clerk_user_id"] = user[0]
                    session["clerk_email"] = user[1]
                    session["clerk_school_id"] = user[3]
                    session["clerk_role"] = "clerk"
                    session.permanent = True

                    print("Clerk login success")

                    return redirect(
                        url_for("clerk_dashboard")
                    )
                
             # FAILED LOGIN
            session["clerk_failed_attempts"] = failed_attempts + 1
            print("❌ Clerk Login Failed")
            return "Invalid Credentials ❌"

        except Exception as e:
            print("❌ LOGIN ERROR:", e)
            return "Login failed ❌"

        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    return render_template("auth/login.html")

# =========================================================
# 🔐 SUPER ADMIN LOGIN
# =========================================================
@app.route("/superadmin/login", methods=["GET", "POST"])
def superadmin_login():
 

    if request.method == "POST":

        email = (request.form.get("email") or "").strip().lower()
        password = (request.form.get("password") or "").strip()

        if not email or not password:
            print("❌ Admin Login Error: Email and password required")
            return "Email and password required ❌"

        failed_attempts = session.get("admin_failed_attempts", 0)

        if failed_attempts >= 5:
            return "Too many failed admin login attempts ❌"
        

        conn = None
        cursor = None

        try:
            conn = get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT id, email, password, role,status
                FROM users
                WHERE email = ?
                AND role = 'admin'
            """, (email,))

            user = cursor.fetchone()

         
            # ================= USER EXISTS =================
            if user:

                db_password = user[2]
                role = user[3]
                status = user[4]

           # ================= ADMIN + HASH CHECK =================
                if (
                    role == "admin"
                    and status == "active"
                    and bcrypt.check_password_hash(
                        db_password,
                        password
                    )
                ):

                    # UPDATE LAST LOGIN
                    cursor.execute("""
                        UPDATE users
                        SET 
                            last_login = GETDATE(),
                            updated_at = GETDATE()
                        WHERE id = ?
                    """, (user[0],))

                    conn.commit()
 
                     

                    # clear admin session
                    session.pop("admin_logged_in", None)
                    session.pop("admin_user_id", None)
                    session.pop("admin_email", None)
                    session.pop("admin_role", None)

                    session.pop("admin_failed_attempts", None)

                    session["admin_logged_in"] = True
                    session["admin_user_id"] = user[0]
                    session["admin_email"] = user[1]
                    session["admin_role"] = "admin"
                    session.permanent = True

                    print("Admin login success")

                    return redirect(
                        url_for("superadmin_dashboard")
                    )
                
                # FAILED LOGIN
            session["admin_failed_attempts"] = failed_attempts + 1
            return "Invalid Admin Credentials ❌"

        except Exception as e:
            print("❌ ADMIN LOGIN ERROR:", e)
            return "Admin login failed ❌"

        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    return render_template("auth/superadmin_login.html")


# =========================================================
# 🚪 LOGOUT ROUTE
# =========================================================
@app.route("/logout", methods=["POST"])
@login_required
def logout():

    role = request.form.get("role")

    if role not in ["clerk", "admin"]:
        return "Invalid logout request ❌"

    # ================= CLERK LOGOUT =================
    if role == "clerk":
        session.pop("clerk_logged_in", None)
        session.pop("clerk_user_id", None)
        session.pop("clerk_email", None)
        session.pop("clerk_school_id", None)
        session.pop("clerk_role", None)
        session.pop("clerk_failed_attempts", None)

        return redirect(url_for("login"))

    # ================= ADMIN LOGOUT =================
    elif role == "admin":
        session.pop("admin_logged_in", None)
        session.pop("admin_user_id", None)
        session.pop("admin_email", None)
        session.pop("admin_role", None)
        session.pop("admin_failed_attempts", None)

        return redirect(url_for("superadmin_login"))
 
 
 # =========================================================
# 📊 SUPER ADMIN DASHBOARD (SAFE)
# =========================================================
@app.route("/superadmin/dashboard")
@admin_required
def superadmin_dashboard():

    conn = None
    cursor = None

    try:
        conn = get_connection()
        cursor = conn.cursor()

        # ================= TOTAL SCHOOLS =================
        cursor.execute("SELECT COUNT(*) FROM schools")
        total_schools = cursor.fetchone()[0]

        # ================= TOTAL STUDENTS =================
        cursor.execute("SELECT COUNT(*) FROM students")
        total_students = cursor.fetchone()[0]

        # ================= TOTAL TC =================
        cursor.execute("SELECT COUNT(*) FROM tc")
        total_tc = cursor.fetchone()[0]

        # ================= TOTAL BONAFIDE =================
        cursor.execute("SELECT COUNT(*) FROM bonafide")
        total_bonafide = cursor.fetchone()[0]

        # ================= CHART DATA =================
        cursor.execute("""
            SELECT 
                s.name,
                COUNT(st.id) AS total_students
            FROM schools s
            LEFT JOIN students st
                ON s.school_id = st.school_id
            GROUP BY s.name
            ORDER BY s.name
        """)
        school_chart = cursor.fetchall()

        chart_labels = []
        chart_values = []

        for row in school_chart:
            chart_labels.append(row[0])
            chart_values.append(row[1])

        # ================= RECENT TC =================
        cursor.execute("""
            SELECT TOP 5
                st.name,
                tc.tc_number,
                tc.tc_date
            FROM tc tc
            JOIN students st
                ON tc.student_id = st.id
            ORDER BY tc.id DESC
        """)
        recent_tc = cursor.fetchall()

        # ================= RECENT BONAFIDE =================
        cursor.execute("""
            SELECT TOP 5
                st.name,
                b.bonafide_number,
                b.created_at
            FROM bonafide b
            JOIN students st
                ON b.student_id = st.id
            ORDER BY b.id DESC
        """)
        recent_bonafide = cursor.fetchall()

        return render_template(
            "dashboard/superadmin.html",
            total_schools=total_schools,
            total_students=total_students,
            total_tc=total_tc,
            total_bonafide=total_bonafide,
            chart_labels=chart_labels,
            chart_values=chart_values,
            recent_tc=recent_tc,
            recent_bonafide=recent_bonafide,
            role="admin",
            active_page="dashboard",
            school_name="SchoolSphere Admin"
        )

    except Exception as e:

        if conn:
            conn.rollback()

        print("❌ ADMIN DASHBOARD ERROR:", e)
        return f"Error loading dashboard ❌ {e}"

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    
 # =========================================================
# 🏫 SUPER ADMIN - ALL SCHOOLS (SAFE)
# =========================================================
@app.route("/superadmin/schools")
@admin_required
def superadmin_schools():

    conn = None
    cursor = None

    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
            s.school_id,
            s.name,
            s.school_code,
            s.udise_no,
            s.address,
            s.phone,
            s.email,
            s.principal_name,
            s.is_active,
                                 
            s.tc_prefix,
            s.bonafide_prefix,

            s.auto_numbering,
            s.enable_certificate_labels,

            s.show_tc_logo,
            s.show_tc_watermark,

            s.show_bonafide_logo,
            s.show_bonafide_watermark,

            COUNT(st.id) AS total_students

        FROM schools s

        LEFT JOIN students st 
            ON s.school_id = st.school_id

        GROUP BY 

            s.school_id,
            s.name,
            s.school_code,
            s.udise_no,
            s.address,
            s.phone,
            s.email,
            s.principal_name,
            s.is_active,
         
            s.tc_prefix,
            s.bonafide_prefix,

            s.auto_numbering,
            s.enable_certificate_labels,

            s.show_tc_logo,
            s.show_tc_watermark,

            s.show_bonafide_logo,
            s.show_bonafide_watermark

        ORDER BY s.school_id DESC

        """)


        rows = cursor.fetchall()

        columns = [col[0] for col in cursor.description]
        schools = [dict(zip(columns, row)) for row in rows]

        # total schools
        total_schools = len(schools)

        # active schools only
        active_schools = sum(
        1 for school in schools
        if int(school["is_active"] or 0) == 1
    )

        return render_template(
            "superadmin/schools.html",
            schools=schools,
            total_schools=total_schools,
            active_schools=active_schools,
            role="admin",
            school_name="Admin",
            active_page="schools"
        )
    
    except Exception as e:
        print("❌ SUPERADMIN SCHOOLS ERROR:", e)
        return "Error loading dashboard ❌"

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# =========================================================
# 💾 SAVE SCHOOL
# =========================================================
@app.route("/superadmin/save-school", methods=["POST"])
@admin_required
def save_school():

    conn = None
    cursor = None

    try:

        # =====================================================
        # GET FORM DATA
        # =====================================================

        name = (
            request.form.get("name") or ""
        ).strip()

        udise_no = (
            request.form.get("udise_no") or ""
        ).strip()

        address = (
            request.form.get("address") or ""
        ).strip()

        phone = (
            request.form.get("phone") or ""
        ).strip()

        email = (
            request.form.get("email") or ""
        ).strip().lower()

        school_code = (
            request.form.get("school_code") or ""
        ).strip()

        principal_name = (
            request.form.get("principal_name") or ""
        ).strip()

        recognition_no = (
            request.form.get("recognition_no") or ""
        ).strip()

        medium = (
            request.form.get("medium") or ""
        ).strip()

        school_index_no = (
            request.form.get("school_index_no") or ""
        ).strip()

        board_name = (
            request.form.get("board_name") or ""
        ).strip()

        # =====================================================
        # VALIDATION
        # =====================================================

        if (
            not name
            or not udise_no
            or not phone
            or not email
            or not school_code
        ):
            return "Required fields missing ❌"

        # =====================================================
        # DB CONNECTION
        # =====================================================

        conn = get_connection()
        cursor = conn.cursor()

        # =====================================================
        # DUPLICATE CHECK
        # =====================================================

        cursor.execute("""
            SELECT school_id
            FROM schools
            WHERE
                udise_no = ?
                OR email = ?
                OR school_code = ?
        """, (

            udise_no,
            email,
            school_code

        ))

        existing_school = cursor.fetchone()

        if existing_school:
            return (
                "School with same UDISE, "
                "Email or School Code already exists ❌"
            )

        # =====================================================
        # GET SYSTEM SETTINGS
        # =====================================================

        cursor.execute("""
            SELECT

                -- SUBSCRIPTION
                default_plan_id,
                trial_days,

                -- CERTIFICATE SETTINGS
                tc_prefix,
                bonafide_prefix,
                auto_numbering,
                enable_certificate_labels,

                show_tc_logo,
                show_tc_watermark,

                show_bonafide_logo,
                show_bonafide_watermark,

                -- FEATURE MODULES
                enable_import_export,
                enable_attendance,
                enable_fee_management,
                enable_teacher_management,
                enable_results,
                enable_timetable,
                enable_notice_board,

                enable_tc_management,
                enable_bonafide_management

            FROM system_settings
            WHERE id = 1
        """)

        settings = cursor.fetchone()

        if not settings:
            return "System settings not found ❌"

        # =====================================================
        # SUBSCRIPTION
        # =====================================================

        default_plan_id = settings[0]
        trial_days = int(settings[1])

        # =====================================================
        # CERTIFICATE SETTINGS
        # =====================================================

        tc_prefix = settings[2]
        bonafide_prefix = settings[3]

        auto_numbering = settings[4]
        enable_certificate_labels = settings[5]

        show_tc_logo = settings[6]
        show_tc_watermark = settings[7]

        show_bonafide_logo = settings[8]
        show_bonafide_watermark = settings[9]

        # =====================================================
        # FEATURE MODULES
        # =====================================================

        enable_import_export = settings[10]
        enable_attendance = settings[11]
        enable_fee_management = settings[12]
        enable_teacher_management = settings[13]
        enable_results = settings[14]
        enable_timetable = settings[15]
        enable_notice_board = settings[16]

        enable_tc_management = settings[17]
        enable_bonafide_management = settings[18]

        # =====================================================
        # INSERT SCHOOL
        # =====================================================

        cursor.execute("""
            INSERT INTO schools (

                -- BASIC INFO
                name,
                udise_no,
                address,
                phone,
                email,
                school_code,
                principal_name,
                recognition_no,
                medium,
                school_index_no,
                board_name,

                -- CERTIFICATE SETTINGS
                tc_prefix,
                bonafide_prefix,
                auto_numbering,
                enable_certificate_labels,

                show_tc_logo,
                show_tc_watermark,

                show_bonafide_logo,
                show_bonafide_watermark,

                -- FEATURE MODULES
                enable_import_export,
                enable_attendance,
                enable_fee_management,
                enable_teacher_management,
                enable_results,
                enable_timetable,
                enable_notice_board,

                enable_tc_management,
                enable_bonafide_management

            )

            VALUES (

                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,

                ?, ?, ?, ?,

                ?, ?,

                ?, ?,

                ?, ?, ?, ?, ?, ?, ?,

                ?, ?

            )
        """, (

            # BASIC INFO
            name,
            udise_no,
            address,
            phone,
            email,
            school_code,
            principal_name,
            recognition_no,
            medium,
            school_index_no,
            board_name,

            # CERTIFICATE SETTINGS
            tc_prefix,
            bonafide_prefix,
            auto_numbering,
            enable_certificate_labels,

            show_tc_logo,
            show_tc_watermark,

            show_bonafide_logo,
            show_bonafide_watermark,

            # FEATURE MODULES
            enable_import_export,
            enable_attendance,
            enable_fee_management,
            enable_teacher_management,
            enable_results,
            enable_timetable,
            enable_notice_board,

            enable_tc_management,
            enable_bonafide_management

        ))

        # =====================================================
        # GET NEW SCHOOL ID
        # =====================================================

        cursor.execute("SELECT @@IDENTITY")

        new_school_id = cursor.fetchone()[0]

        # =====================================================
        # GET PLAN INFO
        # =====================================================

        cursor.execute("""
            SELECT
                plan_name,
                monthly_price
            FROM subscription_plans
            WHERE id = ?
        """, (default_plan_id,))

        plan = cursor.fetchone()

        if not plan:
            return "Default plan not found ❌"

        plan_name = plan[0]
        amount = plan[1]

        start_date = date.today()

        end_date = (
            start_date
            + timedelta(days=trial_days)
        )

        # =====================================================
        # CREATE SUBSCRIPTION
        # =====================================================

        cursor.execute("""
            INSERT INTO subscriptions
            (
                school_id,
                plan_id,
                plan_name,
                start_date,
                end_date,
                status,
                amount
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (

            new_school_id,
            default_plan_id,
            plan_name,
            start_date,
            end_date,
            "active",
            amount

        ))

        # =====================================================
        # SAVE ALL CHANGES
        # =====================================================

        conn.commit()

        # =====================================================
        # SEND WELCOME EMAIL
        # =====================================================

        try:

            subject = (
                "Welcome to ShalaSync ERP"
            )

            body = f"""

            <div style="font-family:Arial;padding:20px;">

                <h2 style="color:#10b981;">
                    Welcome to ShalaSync ERP
                </h2>

                <p>
                    Dear {name},
                </p>

                <p>
                    Your school has been successfully
                    registered in ShalaSync ERP.
                </p>

                <hr>

                <p>
                    <b>School Name:</b>
                    {name}
                </p>

                <p>
                    <b>School Code:</b>
                    {school_code}
                </p>

                <p>
                    <b>UDISE:</b>
                    {udise_no}
                </p>

                <p>
                    <b>Plan:</b>
                    {plan_name}
                </p>

                <p>
                    <b>Trial Valid Till:</b>
                    {end_date}
                </p>

                <hr>

                <p>
                    Thank you for choosing
                    <b>ShalaSync ERP</b>.
                </p>

            </div>

            """

            send_email(
                email,
                subject,
                body
            )

            print(
                "✅ SCHOOL WELCOME EMAIL SENT"
            )

        except Exception as email_error:

            print(
                "❌ WELCOME EMAIL ERROR:",
                email_error
            )

        # =====================================================
        # REDIRECT
        # =====================================================

        return redirect(
            url_for("superadmin_schools")
        )

    except Exception as e:

        if conn:
            conn.rollback()

        print(
            "❌ SAVE SCHOOL ERROR:",
            e
        )

        return f"ERROR ❌ {e}"

    finally:

        if cursor:
            cursor.close()

        if conn:
            conn.close()

# =========================================================
# 💾 UPDATE SCHOOL
# =========================================================
@app.route("/superadmin/update-school", methods=["POST"])
@admin_required
def update_school():

    conn = None
    cursor = None

    try:
        conn = get_connection()
        cursor = conn.cursor()

        # ================= SAFE INPUT =================
        school_id = (request.form.get("school_id") or "").strip()

        name = (request.form.get("name") or "").strip()
        udise_no = (request.form.get("udise_no") or "").strip()
        address = (request.form.get("address") or "").strip()
        phone = (request.form.get("phone") or "").strip()
        email = (request.form.get("email") or "").strip().lower()
        school_code = (request.form.get("school_code") or "").strip()
        principal_name = (request.form.get("principal_name") or "").strip()
        recognition_no = (request.form.get("recognition_no") or "").strip()
        medium = (request.form.get("medium") or "").strip()
        school_index_no = (request.form.get("school_index_no") or "").strip()
        board_name = (request.form.get("board_name") or "").strip()

        # ================= REQUIRED VALIDATION =================
        if (
            not school_id
            or not name
            or not udise_no
            or not phone
            or not email
            or not school_code
        ):
            return "Required fields missing ❌"

        # ================= DUPLICATE CHECK (EXCLUDE CURRENT SCHOOL) =================
        cursor.execute("""
            SELECT school_id
            FROM schools
            WHERE (
                udise_no = ?
                OR email = ?
                OR school_code = ?
            )
            AND school_id != ?
        """, (
            udise_no,
            email,
            school_code,
            school_id
        ))

        duplicate_school = cursor.fetchone()

        if duplicate_school:
            return "School with same UDISE, Email or School Code already exists ❌"

        # ================= UPDATE SCHOOL =================
        cursor.execute("""
            UPDATE schools
            SET
                name = ?,
                udise_no = ?,
                address = ?,
                phone = ?,
                email = ?,
                school_code = ?,
                principal_name = ?,
                recognition_no = ?,
                medium = ?,
                school_index_no = ?,
                board_name = ?
            WHERE school_id = ?
        """, (
            name,
            udise_no,
            address,
            phone,
            email,
            school_code,
            principal_name,
            recognition_no,
            medium,
            school_index_no,
            board_name,
            school_id
        ))

        conn.commit()

        return redirect(
            url_for("superadmin_schools")
        )

    except Exception as e:
        if conn:
            conn.rollback()

        print("❌ UPDATE SCHOOL ERROR:", e)
        return f"Error ❌ {e}"

    finally:
        if cursor:
            cursor.close()

        if conn:
            conn.close()

 # =========================================================
# ⚙ UPDATE SCHOOL FEATURES
# =========================================================

@app.route(
    "/superadmin/update-school-features",
    methods=["POST"]
)
@admin_required
def update_school_features():

    conn = None
    cursor = None

    try:

        # =========================================
        # DB
        # =========================================

        conn = get_connection()
        cursor = conn.cursor()

        # =========================================
        # FORM DATA
        # =========================================

        school_id = (
            request.form.get("school_id") or ""
        ).strip()

        if not school_id:
            return "School ID missing ❌"

        # =========================================
        # FEATURE VALUES
        # =========================================

        enable_tc_management = (
            request.form.get(
                "enable_tc_management"
            ) or "Disabled"
        ).strip()

        enable_bonafide_management = (
            request.form.get(
                "enable_bonafide_management"
            ) or "Disabled"
        ).strip()

        enable_import_export = (
            request.form.get(
                "enable_import_export"
            ) or "Disabled"
        ).strip()

        enable_attendance = (
            request.form.get(
                "enable_attendance"
            ) or "Disabled"
        ).strip()

        enable_fee_management = (
            request.form.get(
                "enable_fee_management"
            ) or "Disabled"
        ).strip()

        enable_teacher_management = (
            request.form.get(
                "enable_teacher_management"
            ) or "Disabled"
        ).strip()

        enable_results = (
            request.form.get(
                "enable_results"
            ) or "Disabled"
        ).strip()

        enable_timetable = (
            request.form.get(
                "enable_timetable"
            ) or "Disabled"
        ).strip()

        enable_notice_board = (
            request.form.get(
                "enable_notice_board"
            ) or "Disabled"
        ).strip()

        # =========================================
        # UPDATE SCHOOL
        # =========================================

        cursor.execute("""

            UPDATE schools
            SET

                enable_tc_management = ?,
                enable_bonafide_management = ?,

                enable_import_export = ?,
                enable_attendance = ?,
                enable_fee_management = ?,
                enable_teacher_management = ?,
                enable_results = ?,
                enable_timetable = ?,
                enable_notice_board = ?

            WHERE school_id = ?

        """, (

            enable_tc_management,
            enable_bonafide_management,

            enable_import_export,
            enable_attendance,
            enable_fee_management,
            enable_teacher_management,
            enable_results,
            enable_timetable,
            enable_notice_board,

            school_id
        ))

        conn.commit()

        return redirect(
            url_for("superadmin_schools")
        )

    except Exception as e:

        if conn:
            conn.rollback()

        print(
            "❌ UPDATE SCHOOL FEATURES ERROR:",
            e
        )

        return f"ERROR ❌ {e}"

    finally:

        if cursor:
            cursor.close()

        if conn:
            conn.close()

# =========================================================
# 📜 UPDATE SCHOOL CERTIFICATE SETTINGS
# =========================================================
@app.route(
    "/superadmin/update-school-certificates",
    methods=["POST"]
)
@admin_required
def update_school_certificates():

    conn = None
    cursor = None

    try:

        # =========================================
        # DB
        # =========================================

        conn = get_connection()
        cursor = conn.cursor()

        # =========================================
        # GET SCHOOL ID
        # =========================================

        school_id = (
            request.form.get("school_id") or ""
        ).strip()

        if not school_id:
            return "School ID missing ❌"

        # =========================================
        # CERTIFICATE SETTINGS
        # =========================================

        tc_prefix = (
            request.form.get(
                "tc_prefix"
            ) or "TC"
        ).strip().upper()

        bonafide_prefix = (
            request.form.get(
                "bonafide_prefix"
            ) or "BON"
        ).strip().upper()

        auto_numbering = (
            request.form.get(
                "auto_numbering"
            ) or "Enabled"
        ).strip()

        enable_certificate_labels = (
            request.form.get(
                "enable_certificate_labels"
            ) or "Enabled"
        ).strip()

        show_tc_logo = (
            request.form.get(
                "show_tc_logo"
            ) or "Disabled"
        ).strip()

        show_tc_watermark = (
            request.form.get(
                "show_tc_watermark"
            ) or "Disabled"
        ).strip()

        show_bonafide_logo = (
            request.form.get(
                "show_bonafide_logo"
            ) or "Disabled"
        ).strip()

        show_bonafide_watermark = (
            request.form.get(
                "show_bonafide_watermark"
            ) or "Disabled"
        ).strip()

        # =========================================
        # UPDATE SCHOOL
        # =========================================

        cursor.execute("""

            UPDATE schools
            SET

                tc_prefix = ?,
                bonafide_prefix = ?,

                auto_numbering = ?,
                enable_certificate_labels = ?,

                show_tc_logo = ?,
                show_tc_watermark = ?,

                show_bonafide_logo = ?,
                show_bonafide_watermark = ?

            WHERE school_id = ?

        """, (

            tc_prefix,
            bonafide_prefix,

            auto_numbering,
            enable_certificate_labels,

            show_tc_logo,
            show_tc_watermark,

            show_bonafide_logo,
            show_bonafide_watermark,

            school_id

        ))

        conn.commit()

        return redirect(
            url_for("superadmin_schools")
        )

    except Exception as e:

        if conn:
            conn.rollback()

        print(
            "❌ SCHOOL CERTIFICATE SETTINGS ERROR:",
            e
        )

        return f"ERROR ❌ {e}"

    finally:

        if cursor:
            cursor.close()

        if conn:
            conn.close()
            
# =========================================================
# 🔄 TOGGLE SCHOOL STATUS (ACTIVE/INACTIVE)
# =========================================================
@app.route("/superadmin/toggle-school-status", methods=["POST"])
@admin_required
def toggle_school_status():

    conn = None
    cursor = None

    try:
        # ================= SAFE INPUT =================
        school_id = (request.form.get("school_id") or "").strip()

        if not school_id:
            return "School ID missing ❌"

        print("School ID received:", school_id)

        conn = get_connection()
        cursor = conn.cursor()

        # ================= CHECK SCHOOL EXISTS =================
        cursor.execute("""
            SELECT school_id
            FROM schools
            WHERE school_id = ?
        """, (school_id,))

        school = cursor.fetchone()

        if not school:
            return "School not found ❌"

        # ================= TOGGLE STATUS =================
        cursor.execute("""
            UPDATE schools
            SET is_active =
                CASE
                    WHEN is_active = 1 THEN 0
                    ELSE 1
                END
            WHERE school_id = ?
        """, (school_id,))

        print("Rows affected:", cursor.rowcount)

        conn.commit()

        print("Status updated successfully")

        return redirect(
            url_for("superadmin_schools")
        )

    except Exception as e:
        if conn:
            conn.rollback()

        print("STATUS TOGGLE ERROR:", e)
        return f"Error ❌ {e}"

    finally:
        if cursor:
            cursor.close()

        if conn:
            conn.close()
            

# =========================================================
# 👨‍🎓 SUPER ADMIN - STUDENTS BY SCHOOL (SAFE)
# =========================================================
@app.route("/superadmin/superadmin_students")
@admin_required
def superadmin_students():

    conn = None
    cursor = None

    try:
        school_id = (request.args.get("school_id") or "").strip()

        if not school_id:
            return "School ID missing ❌"

        conn = get_connection()
        cursor = conn.cursor()

        # ================= GET SCHOOL =================
        cursor.execute("""
            SELECT name
            FROM schools
            WHERE school_id = ?
        """, (school_id,))

        school = cursor.fetchone()

        if not school:
            return "School not found ❌"

        # ================= GET STUDENTS =================
        cursor.execute("""
            SELECT 
                id,
                name,
                [class],
                admission_no,
                primary_mobile
            FROM students
            WHERE school_id = ?
            ORDER BY id DESC
        """, (school_id,))

        students = cursor.fetchall()

        return render_template(
            "superadmin/superadmin_students.html",
            students=students,
            school_name=school[0],
            role="admin"
        )

    except Exception as e:

        if conn:
            conn.rollback()

        print("❌ SUPERADMIN STUDENTS ERROR:", e)
        return f"Error loading students ❌ {e}"

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


# =========================================================
# 📦 GET STUDENT DATA (API FOR MODAL) FOR ADMIN (SAFE)
# =========================================================
@app.route("/get-student/<int:id>")
@admin_required
def get_student(id):

    conn = None
    cursor = None

    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * 
            FROM students 
            WHERE id = ?
        """, (id,))

        row = cursor.fetchone()

        if not row:
            return {"error": "Student not found"}

        columns = [col[0] for col in cursor.description]
        student = dict(zip(columns, row))

        return jsonify(student)

    except Exception as e:
        print("❌ GET STUDENT ERROR:", e)
        return {"error": str(e)}

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


# =========================================================
# ❌ DELETE STUDENT (ADMIN SAFE)
# =========================================================
@app.route("/superadmin/delete_student", methods=["POST"])
@admin_required
def delete_student():

    conn = None
    cursor = None

    try:

        # ================= GET STUDENT ID =================
        student_id = request.form.get("student_id")

        if not student_id:
            return "Invalid student ID ❌"

        conn = get_connection()
        cursor = conn.cursor()

        # ================= CHECK STUDENT =================
        cursor.execute("""
            SELECT id
            FROM students
            WHERE id = ?
        """, (student_id,))

        student = cursor.fetchone()

        if not student:
            return "Student not found ❌"

        # ================= CHECK TC RECORDS =================
        cursor.execute("""
            SELECT COUNT(*)
            FROM tc
            WHERE student_id = ?
        """, (student_id,))

        tc_count = cursor.fetchone()[0]

        if tc_count > 0:
            return "Cannot delete: TC records exist ❌"

        # ================= CHECK BONAFIDE RECORDS =================
        cursor.execute("""
            SELECT COUNT(*)
            FROM bonafide
            WHERE student_id = ?
        """, (student_id,))

        bonafide_count = cursor.fetchone()[0]

        if bonafide_count > 0:
            return "Cannot delete: Bonafide records exist ❌"

        # ================= DELETE STUDENT =================
        cursor.execute("""
            DELETE FROM students
            WHERE id = ?
        """, (student_id,))

        conn.commit()

        return redirect(
            request.referrer
            or url_for("superadmin_schools")
        )

    except Exception as e:

        if conn:
            conn.rollback()

        print("❌ DELETE STUDENT ERROR:", e)

        return f"Delete Error ❌ {e}"

    finally:

        if cursor:
            cursor.close()

        if conn:
            conn.close()


# =========================================================
# 👨‍🎓 SUPER ADMIN - ALL STUDENTS (SAFE + PAGINATION)
# =========================================================
@app.route("/superadmin/all-students")
@admin_required
def superadmin_all_students():

    conn = None
    cursor = None

    try:
        conn = get_connection()
        cursor = conn.cursor()

        # ================= GET PARAMS =================
        page = request.args.get("page", 1, type=int)
        per_page = 10

        search = request.args.get("search", "").strip()
        school_id = request.args.get("school_id", type=int)

        if page < 1:
            page = 1

        offset = (page - 1) * per_page

        # ================= WHERE =================
        where = "WHERE 1=1"
        params = []

        if school_id:
            where += " AND st.school_id = ?"
            params.append(school_id)

        if search:
            where += """
            AND (
                st.name LIKE ?
                OR st.admission_no LIKE ?
                OR st.primary_mobile LIKE ?
            )
            """
            like = f"%{search}%"
            params.extend([like, like, like])

        # ================= TOTAL COUNT =================
        cursor.execute(f"""
            SELECT COUNT(*)
            FROM students st
            {where}
        """, params)

        total = cursor.fetchone()[0]
        total_pages = (total + per_page - 1) // per_page

        # PAGE SAFETY
        if total_pages > 0 and page > total_pages:
            page = total_pages
            offset = (page - 1) * per_page

        # ================= GET STUDENTS =================
        cursor.execute(f"""
            SELECT
                st.id,
                st.name,
                st.[class],
                st.admission_no,
                st.primary_mobile,
                sc.name AS school_name,
                sc.school_id
            FROM students st
            JOIN schools sc
                ON st.school_id = sc.school_id
            {where}
            ORDER BY st.id DESC
            OFFSET ? ROWS
            FETCH NEXT ? ROWS ONLY
        """, (*params, offset, per_page))

        students = cursor.fetchall()

        # ================= GET SCHOOLS =================
        cursor.execute("""
            SELECT school_id, name
            FROM schools
            ORDER BY name
        """)
        schools = cursor.fetchall()

        return render_template(
            "superadmin/superadmin_all_students.html",
            students=students,
            schools=schools,
            total=total,
            page=page,
            total_pages=total_pages,
            search=search,
            selected_school=school_id,
            role="admin",
            school_name="Admin Panel",
            active_page="all-students"
        )

    except Exception as e:
 
        print("❌ ALL STUDENTS ERROR:", e)
        return f"Error loading students ❌ {e}"

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# =========================================================
# 🧾 SUPER ADMIN - TC MANAGEMENT (SAFE)
# =========================================================
@app.route("/superadmin/tc-management")
@admin_required
def superadmin_tc_management():

    conn = None
    cursor = None

    try:
        conn = get_connection()
        cursor = conn.cursor()

        search = (request.args.get("search") or "").strip()
        school_filter = (request.args.get("school_id") or "").strip()
        class_filter = (request.args.get("class") or "").strip()

        query = """
            SELECT
                tc.id,
                st.name,
                st.admission_no,
                st.[class],
                sc.name AS school_name,
                tc.tc_number,
                tc.leaving_date,
                tc.leaving_reason,
                tc.tc_date,
                sc.school_id
            FROM tc
            JOIN students st
                ON tc.student_id = st.id
            JOIN schools sc
                ON tc.school_id = sc.school_id
            WHERE 1=1
        """

        params = []

        # ================= SEARCH =================
        if search:
            query += """
                AND (
                    st.name LIKE ?
                    OR st.admission_no LIKE ?
                    OR tc.tc_number LIKE ?
                )
            """
            params.extend([
                f"%{search}%",
                f"%{search}%",
                f"%{search}%"
            ])

        # ================= SCHOOL FILTER =================
        if school_filter:
            query += " AND sc.school_id = ?"
            params.append(school_filter)

        # ================= CLASS FILTER =================
        if class_filter:
            query += " AND st.[class] = ?"
            params.append(class_filter)

        query += " ORDER BY tc.id DESC"

        cursor.execute(query, params)
        tc_records = cursor.fetchall()

        # ================= SCHOOLS =================
        cursor.execute("""
            SELECT school_id, name
            FROM schools
            ORDER BY name
        """)
        schools = cursor.fetchall()

        # ================= TOTAL TC =================
        cursor.execute("""
            SELECT COUNT(*)
            FROM tc
        """)
        total_tc = cursor.fetchone()[0]

        # ================= LAST 7 DAYS =================
        cursor.execute("""
            SELECT COUNT(*)
            FROM tc
            WHERE CAST(tc_date AS DATE)
            = CAST(GETDATE() AS DATE)
        """)
        today_tc = cursor.fetchone()[0]

        # ================= THIS MONTH =================
        cursor.execute("""
            SELECT COUNT(*)
            FROM tc
            WHERE MONTH(tc_date) = MONTH(GETDATE())
            AND YEAR(tc_date) = YEAR(GETDATE())
        """)
        month_tc = cursor.fetchone()[0]

        # ================= ACTIVE SCHOOLS =================
        cursor.execute("""
            SELECT COUNT(DISTINCT school_id)
            FROM tc
        """)
        school_tc_count = cursor.fetchone()[0]

        return render_template(
            "superadmin/superadmin_tc.html",
            active_page="tc-management",
            tc_records=tc_records,
            schools=schools,
            total_tc=total_tc,
            today_tc=today_tc,
            month_tc=month_tc,
            school_tc_count=school_tc_count,
            role="admin",
            school_name="Admin Panel"
        )

    except Exception as e:
        
        print("❌ TC MANAGEMENT ERROR:", e)
        return f"TC Management Error ❌ {e}"

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
            
 # =========================================================
# ❌ DELETE TC (ADMIN SAFE)
# =========================================================
@app.route("/superadmin/delete-tc", methods=["POST"])
@admin_required
def delete_tc():

    conn = None
    cursor = None

    try:

        # ================= GET TC ID =================
        tc_id = (request.form.get("tc_id") or "").strip()

        if not tc_id:
            return "Invalid TC ID ❌"

        conn = get_connection()
        cursor = conn.cursor()

        # ================= CHECK TC EXISTS =================
        cursor.execute("""
            SELECT id
            FROM tc
            WHERE id = ?
        """, (tc_id,))

        tc = cursor.fetchone()

        if not tc:
            return "TC record not found ❌"

        # ================= DELETE TC =================
        cursor.execute("""
            DELETE FROM tc
            WHERE id = ?
        """, (tc_id,))

        conn.commit()

        return redirect(
            request.referrer or url_for("superadmin_tc_management")
        )

    except Exception as e:

        if conn:
            conn.rollback()

        print("❌ DELETE TC ERROR:", e)

        return f"Delete TC Error ❌ {e}"

    finally:

        if cursor:
            cursor.close()

        if conn:
            conn.close()

 # =========================================================
# 📜 SUPER ADMIN - BONAFIDE MANAGEMENT (SAFE)
# =========================================================
@app.route("/superadmin/bonafide-management")
@admin_required
def superadmin_bonafide_management():

    conn = None
    cursor = None

    try:
        conn = get_connection()
        cursor = conn.cursor()

        search = (request.args.get("search") or "").strip()
        school_filter = (request.args.get("school_id") or "").strip()
        class_filter = (request.args.get("class") or "").strip()

        query = """
            SELECT
                b.id,
                s.name,
                s.admission_no,
                s.[class],
                sc.name AS school_name,
                b.bonafide_number,
                b.purpose,
                b.date,
                sc.school_id
            FROM bonafide b
            JOIN students s
                ON b.student_id = s.id
            JOIN schools sc
                ON b.school_id = sc.school_id
            WHERE 1=1
        """

        params = []

        # ================= SEARCH =================
        if search:
            query += """
                AND (
                    s.name LIKE ?
                    OR s.admission_no LIKE ?
                    OR b.bonafide_number LIKE ?
                )
            """
            params.extend([
                f"%{search}%",
                f"%{search}%",
                f"%{search}%"
            ])

        # ================= SCHOOL FILTER =================
        if school_filter:
            query += " AND sc.school_id = ?"
            params.append(school_filter)

        # ================= CLASS FILTER =================
        if class_filter:
            query += " AND s.[class] = ?"
            params.append(class_filter)

        query += " ORDER BY b.id DESC"

        cursor.execute(query, params)
        bonafides = cursor.fetchall()

        # ================= SCHOOLS =================
        cursor.execute("""
            SELECT school_id, name
            FROM schools
            ORDER BY name
        """)
        schools = cursor.fetchall()

        # ================= TOTAL =================
        cursor.execute("""
            SELECT COUNT(*)
            FROM bonafide
        """)
        total_bonafide = cursor.fetchone()[0]

        # ================= THIS MONTH =================
        cursor.execute("""
            SELECT COUNT(*)
            FROM bonafide
            WHERE MONTH(date) = MONTH(GETDATE())
            AND YEAR(date) = YEAR(GETDATE())
        """)
        month_bonafide = cursor.fetchone()[0]

        # ================= LAST 7 DAYS =================
        cursor.execute("""
            SELECT COUNT(*)
            FROM bonafide
            WHERE date >= DATEADD(
                DAY, -7, CAST(GETDATE() AS DATE)
            )
        """)
        week_bonafide = cursor.fetchone()[0]

        # ================= ACTIVE SCHOOLS =================
        cursor.execute("""
            SELECT COUNT(DISTINCT school_id)
            FROM bonafide
        """)
        school_count = cursor.fetchone()[0]

        return render_template(
            "superadmin/superadmin_bonafide.html",
            active_page="bonafide-management",
            bonafides=bonafides,
            schools=schools,
            total_bonafide=total_bonafide,
            month_bonafide=month_bonafide,
            week_bonafide=week_bonafide,
            school_count=school_count,
            role="admin",
            school_name="Admin Panel"
        )

    except Exception as e:

 

        print("❌ BONAFIDE MANAGEMENT ERROR:", e)
        return f"Bonafide Management Error ❌ {e}"

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# =========================================================
# ❌ DELETE BONAFIDE (ADMIN SAFE)
# =========================================================
@app.route("/superadmin/delete-bonafide", methods=["POST"])
@admin_required
def delete_bonafide():

    conn = None
    cursor = None

    try:

        bonafide_id = (request.form.get("bonafide_id") or "").strip()

        if not bonafide_id:
            return "Invalid bonafide ID ❌"

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id
            FROM bonafide
            WHERE id = ?
        """, (bonafide_id,))

        bonafide = cursor.fetchone()

        if not bonafide:
            return "Bonafide record not found ❌"

        cursor.execute("""
            DELETE FROM bonafide
            WHERE id = ?
        """, (bonafide_id,))

        conn.commit()

        return redirect(
            request.referrer or "/superadmin/bonafide-management"
        )

    except Exception as e:

        print("❌ DELETE BONAFIDE ERROR:", e)

        return f"Delete Bonafide Error ❌ {e}"

    finally:

        if cursor:
            cursor.close()

        if conn:
            conn.close()

# =========================================================
# 👥 SUPER ADMIN - USERS MANAGEMENT (SAFE)
# =========================================================
@app.route("/superadmin/users")
@admin_required
def superadmin_users():

    conn = None
    cursor = None

    try:
        conn = get_connection()
        cursor = conn.cursor()

        search = request.args.get("search", "").strip()
        role_filter = request.args.get("role", "").strip()
        status_filter = request.args.get("status", "").strip()

        query = """
            SELECT 
                u.id,
                u.name,
                u.email,
                u.phone,
                u.role,
                u.status,
                u.last_login,
                u.created_at,
                s.name AS school_name
            FROM users u
            LEFT JOIN schools s
                ON u.school_id = s.school_id
            WHERE 1=1
        """

        params = []

        # ================= SEARCH =================
        if search:
            query += """
                AND (
                    u.name LIKE ?
                    OR u.email LIKE ?
                    OR u.phone LIKE ?
                )
            """
            params.extend([
                f"%{search}%",
                f"%{search}%",
                f"%{search}%"
            ])

        # ================= ROLE FILTER =================
        if role_filter:
            query += " AND u.role = ?"
            params.append(role_filter)

        # ================= STATUS FILTER =================
        if status_filter:
            query += " AND u.status = ?"
            params.append(status_filter)

        query += " ORDER BY u.id DESC"

        cursor.execute(query, params)

        rows = cursor.fetchall()

        columns = [col[0] for col in cursor.description]
        users = [dict(zip(columns, row)) for row in rows]

        # ================= TOTAL USERS =================
        cursor.execute("""
            SELECT COUNT(*)
            FROM users
        """)
        total_users = cursor.fetchone()[0]

        # ================= ACTIVE USERS =================
        cursor.execute("""
            SELECT COUNT(*)
            FROM users
            WHERE status = 'active'
        """)
        active_users = cursor.fetchone()[0]

        # ================= CLERKS =================
        cursor.execute("""
            SELECT COUNT(*)
            FROM users
            WHERE role = 'clerk'
        """)
        clerk_users = cursor.fetchone()[0]

        # ================= ADMINS =================
        cursor.execute("""
            SELECT COUNT(*)
            FROM users
            WHERE role = 'admin'
        """)
        admin_users = cursor.fetchone()[0]

        return render_template(
            "superadmin/superadmin_users.html",
            users=users,
            total_users=total_users,
            active_users=active_users,
            clerk_users=clerk_users,
            admin_users=admin_users,
            role="admin",
            school_name="Admin Panel",
            active_page="users"
        )

    except Exception as e:

        if conn:
            conn.rollback()

        print("❌ USERS MANAGEMENT ERROR:", e)
        return f"Users Management Error ❌ {e}"

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
# =========================================================
# ✏️ SUPER ADMIN - EDIT USER (SAFE)
# =========================================================
@app.route("/superadmin/user/edit/<int:user_id>", methods=["POST"])
@admin_required
def superadmin_edit_user(user_id):

    conn = None
    cursor = None

    try:
        conn = get_connection()
        cursor = conn.cursor()

        name = (request.form.get("name") or "").strip()
        email = (request.form.get("email") or "").strip().lower()
        phone = (request.form.get("phone") or "").strip()
        role = (request.form.get("role") or "").strip()

        # VALIDATION
        if not name or not email or not role:
            return "Required fields missing ❌"

        # USER EXISTS
        cursor.execute("""
            SELECT id
            FROM users
            WHERE id = ?
        """, (user_id,))

        user = cursor.fetchone()

        if not user:
            return "User not found ❌"

        # DUPLICATE EMAIL CHECK
        cursor.execute("""
            SELECT id
            FROM users
            WHERE email = ?
            AND id != ?
        """, (email, user_id))

        duplicate = cursor.fetchone()

        if duplicate:
            return "Email already exists ❌"

        # UPDATE
        cursor.execute("""
            UPDATE users
            SET
                name = ?,
                email = ?,
                phone = ?,
                role = ?,
                updated_at = GETDATE()
            WHERE id = ?
        """, (
            name,
            email,
            phone,
            role,
            user_id
        ))

        conn.commit()

        return redirect(
            request.referrer
            or url_for("superadmin_users")
        )

    except Exception as e:

        if conn:
            conn.rollback()

        print("❌ EDIT USER ERROR:", e)
        return f"Edit User Error ❌ {e}"

    finally:
        if cursor:
            cursor.close()

        if conn:
            conn.close()
 
# =========================================================
# 🔄 SUPER ADMIN - TOGGLE USER STATUS (SAFE)
# =========================================================
@app.route("/superadmin/user/status", methods=["POST"])
@admin_required
def superadmin_toggle_user_status():

    conn = None
    cursor = None

    try:
        user_id = (request.form.get("user_id") or "").strip()

        if not user_id:
            return "Invalid user ID ❌"

        conn = get_connection()
        cursor = conn.cursor()

        # CHECK USER
        cursor.execute("""
            SELECT status
            FROM users
            WHERE id = ?
        """, (user_id,))

        user = cursor.fetchone()

        if not user:
            return "User not found ❌"

        # PREVENT SELF BLOCK
        if session.get("admin_user_id") == int(user_id):
            return "You cannot change your own status ❌"

        current_status = user[0]

        new_status = (
            "blocked"
            if current_status == "active"
            else "active"
        )

        # UPDATE STATUS
        cursor.execute("""
            UPDATE users
            SET
                status = ?,
                updated_at = GETDATE()
            WHERE id = ?
        """, (
            new_status,
            user_id
        ))

        conn.commit()

        return redirect(
            request.referrer
            or url_for("superadmin_users")
        )

    except Exception as e:

        if conn:
            conn.rollback()

        print("❌ TOGGLE STATUS ERROR:", e)
        return f"Status Toggle Error ❌ {e}"

    finally:
        if cursor:
            cursor.close()

        if conn:
            conn.close()
 
# =========================================================
# ❌ SUPER ADMIN - DELETE USER (SAFE)
# =========================================================
@app.route("/superadmin/user/delete", methods=["POST"])
@admin_required
def superadmin_delete_user():

    user_id = (
        request.form.get("user_id") or ""
    ).strip()

    conn = None
    cursor = None

    try:
        if not user_id:
            return "Invalid user ID ❌"

        conn = get_connection()
        cursor = conn.cursor()

        # CHECK USER
        cursor.execute("""
            SELECT role
            FROM users
            WHERE id = ?
        """, (user_id,))

        user = cursor.fetchone()

        if not user:
            return "User not found ❌"

        # PREVENT ADMIN DELETE
        if user[0] == "admin":
            return "Admin account cannot be deleted ❌"

        # PREVENT SELF DELETE
        if session.get("admin_user_id") == int(user_id):
            return "You cannot delete your own account ❌"

        # DELETE
        cursor.execute("""
            DELETE FROM users
            WHERE id = ?
        """, (user_id,))

        conn.commit()

        return redirect(
            url_for("superadmin_users")
        )

    except Exception as e:

        if conn:
            conn.rollback()

        print("❌ DELETE USER ERROR:", e)
        return f"Delete User Error ❌ {e}"

    finally:
        if cursor:
            cursor.close()

        if conn:
            conn.close()

# =========================================================
# ⚙️ SUPER ADMIN - SETTINGS PAGE (UPDATED)
# =========================================================
@app.route("/superadmin/settings")
@admin_required
def superadmin_settings():

    conn = None
    cursor = None

    try:
        conn = get_connection()
        cursor = conn.cursor()

        # ================= TOTAL SCHOOLS =================
        cursor.execute("""
            SELECT COUNT(*)
            FROM schools
        """)
        total_schools = cursor.fetchone()[0]

        # ================= SETTINGS =================
        cursor.execute("""
            SELECT TOP 1 *
            FROM system_settings
            ORDER BY id ASC
        """)
        row = cursor.fetchone()

        settings = {}

        if row:
            columns = [col[0] for col in cursor.description]
            settings = dict(zip(columns, row))

        # ================= SUBSCRIPTION PLANS =================
        cursor.execute("""
            SELECT
                id,
                plan_name,
                monthly_price
            FROM subscription_plans
            WHERE is_active = 1
            ORDER BY monthly_price ASC
        """)

        plan_rows = cursor.fetchall()

        plans = []

        for p in plan_rows:
            plans.append({
                "id": p[0],
                "plan_name": p[1],
                "monthly_price": p[2]
            })

       # ================= BACKUP LOGS =================

        cursor.execute("""

            SELECT TOP 10

                id,
                backup_file,
                backup_status,
                backup_size,
                backup_date,
                backup_type

            FROM system_backup_logs

            ORDER BY id DESC

        """)

        backup_logs = cursor.fetchall()

        return render_template(
            "superadmin/superadmin_settings.html",
            settings=settings,
            plans=plans,
            backup_logs=backup_logs,
            total_schools=total_schools,
            role="admin",
            school_name="Admin Panel",
            active_page="settings"
        )

    except Exception as e:

        print("❌ SETTINGS ERROR:", e)
        return f"Settings Error ❌ {e}"

    finally:
        if cursor:
            cursor.close()

        if conn:
            conn.close()
            
 # =========================================================
# 💾 SAVE GENERAL SETTINGS
# =========================================================
@app.route("/superadmin/settings/general", methods=["POST"])
@admin_required
def save_general_settings():

    conn = None
    cursor = None

    try:

        # ================= GET FORM DATA =================

        system_name = (
            request.form.get("system_name") or ""
        ).strip()

        support_email = (
            request.form.get("support_email") or ""
        ).strip()

        support_phone = (
            request.form.get("support_phone") or ""
        ).strip()

        default_language = (
            request.form.get("default_language") or ""
        ).strip()

        timezone = (
            request.form.get("timezone") or ""
        ).strip()

        # ================= VALIDATION =================

        if not system_name:
            return "System name required ❌"

        conn = get_connection()
        cursor = conn.cursor()

        # ================= LOGO UPLOAD =================

        logo_filename = None

        if "system_logo" in request.files:

            logo = request.files["system_logo"]

            if logo and logo.filename != "":

                filename = secure_filename(
                    logo.filename
                )

                upload_path = os.path.join(
                    "static/uploads",
                    filename
                )

                os.makedirs("static/uploads", exist_ok=True)

                logo.save(upload_path)

                logo_filename = (
                    "uploads/" + filename
                )

        # ================= UPDATE SETTINGS =================

        if logo_filename:

            cursor.execute("""
                UPDATE system_settings
                SET
                    system_name = ?,
                    support_email = ?,
                    support_phone = ?,
                    default_language = ?,
                    timezone = ?,
                    system_logo = ?,
                    updated_at = GETDATE()
                WHERE id = 1
            """, (
                system_name,
                support_email,
                support_phone,
                default_language,
                timezone,
                logo_filename
            ))

        else:

            cursor.execute("""
                UPDATE system_settings
                SET
                    system_name = ?,
                    support_email = ?,
                    support_phone = ?,
                    default_language = ?,
                    timezone = ?,
                    updated_at = GETDATE()
                WHERE id = 1
            """, (
                system_name,
                support_email,
                support_phone,
                default_language,
                timezone
            ))

        conn.commit()

        return redirect(
            url_for("superadmin_settings")
        )

    except Exception as e:

        if conn:
            conn.rollback()

        print("❌ GENERAL SETTINGS ERROR:", e)

        return f"General Settings Error ❌ {e}"

    finally:

        if cursor:
            cursor.close()

        if conn:
            conn.close()


# =========================================================
# 💳 SAVE SUBSCRIPTION SETTINGS
# =========================================================
@app.route("/superadmin/settings/subscription", methods=["POST"])
@admin_required
def save_subscription_settings():

    conn = None
    cursor = None

    try:

        # =====================================================
        # GET FORM DATA
        # =====================================================

        default_plan_id = (
            request.form.get("default_plan_id", "")
        ).strip()

        trial_days = (
            request.form.get("trial_days", "")
        ).strip()

        grace_period = (
            request.form.get("grace_period", "")
        ).strip()

        # =====================================================
        # VALIDATION
        # =====================================================

        if not default_plan_id:
            return "Default plan missing ❌"

        if not trial_days:
            return "Trial days missing ❌"

        if not grace_period:
            return "Grace period missing ❌"

        if not default_plan_id.isdigit():
            return "Invalid default plan ❌"

        if not trial_days.isdigit():
            return "Invalid trial days ❌"

        if not grace_period.isdigit():
            return "Invalid grace period ❌"

        # =====================================================
        # DB CONNECTION
        # =====================================================

        conn = get_connection()
        cursor = conn.cursor()

        # =====================================================
        # CHECK PLAN EXISTS
        # =====================================================

        cursor.execute("""
            SELECT
                id,
                plan_name
            FROM subscription_plans
            WHERE id = ?
            AND is_active = 1
        """, (int(default_plan_id),))

        plan = cursor.fetchone()

        if not plan:
            return "Selected subscription plan not found ❌"

        # =====================================================
        # CHECK SETTINGS EXISTS
        # =====================================================

        cursor.execute("""
            SELECT id
            FROM system_settings
            WHERE id = 1
        """)

        settings = cursor.fetchone()

        if not settings:
            return "System settings not found ❌"

        # =====================================================
        # UPDATE SETTINGS
        # =====================================================

        cursor.execute("""
            UPDATE system_settings
            SET
                default_plan_id = ?,
                trial_days = ?,
                grace_period = ?,
                updated_at = GETDATE()
            WHERE id = 1
        """, (
            int(default_plan_id),
            int(trial_days),
            int(grace_period)
        ))

        conn.commit()

        return redirect(
            url_for("superadmin_settings")
        )

    except Exception as e:

        if conn:
            conn.rollback()

        print("❌ SUBSCRIPTION SETTINGS ERROR:", e)

        return f"Subscription Settings Error ❌ {e}"

    finally:

        if cursor:
            cursor.close()

        if conn:
            conn.close()

# =========================================================
# 🔐 SAVE SECURITY SETTINGS (SAFE)
# =========================================================
@app.route("/superadmin/settings/security", methods=["POST"])
@admin_required
def save_security_settings():

    conn = None
    cursor = None

    try:
        password_length = request.form.get(
            "password_length", ""
        ).strip()

        login_attempt_limit = request.form.get(
            "login_attempt_limit", ""
        ).strip()

        session_timeout = request.form.get(
            "session_timeout", ""
        ).strip()

        # ================= VALIDATION =================
        if (
            not password_length
            or not login_attempt_limit
            or not session_timeout
        ):
            return "Required fields missing ❌"

        if not password_length.isdigit():
            return "Invalid password length ❌"

        if not login_attempt_limit.isdigit():
            return "Invalid login attempt limit ❌"

        if not session_timeout.isdigit():
            return "Invalid session timeout ❌"

        conn = get_connection()
        cursor = conn.cursor()

        # ================= CHECK SETTINGS =================
        cursor.execute("""
            SELECT id
            FROM system_settings
            WHERE id = 1
        """)

        settings = cursor.fetchone()

        if not settings:
            return "System settings not found ❌"

        # ================= UPDATE =================
        cursor.execute("""
            UPDATE system_settings
            SET
                password_length = ?,
                login_attempt_limit = ?,
                session_timeout = ?,
                updated_at = GETDATE()
            WHERE id = 1
        """, (
            int(password_length),
            int(login_attempt_limit),
            int(session_timeout)
        ))

        conn.commit()

        return redirect(
            url_for("superadmin_settings")
        )

    except Exception as e:

        if conn:
            conn.rollback()

        print("❌ SECURITY SETTINGS ERROR:", e)
        return f"Security Settings Error ❌ {e}"

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


 
# =========================================================
# 💳 SUBSCRIPTION RENEW PAGE
# =========================================================
@app.route("/clerk/subscription/renew")
@login_required
def renew_subscription():

    school_id = session.get("clerk_school_id")

    if not school_id:
        return "School session missing ❌"

    conn = None
    cursor = None

    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT TOP 1
                s.id,
                s.plan_id,
                p.plan_name,
                s.amount,
                s.end_date,
                s.status
            FROM subscriptions s
            INNER JOIN subscription_plans p
                ON s.plan_id = p.id
            WHERE s.school_id = ?
            ORDER BY s.id DESC
        """, (school_id,))

        row = cursor.fetchone()

        if not row:
            return "Subscription not found ❌"

        subscription = {
            "id": row[0],
            "plan_id": row[1],
            "plan_name": row[2],
            "amount": row[3],
            "end_date": row[4],
            "status": row[5]
        }

        # ================= ALL ACTIVE PLANS =================
        cursor.execute("""
            SELECT
                id,
                plan_name,
                monthly_price
            FROM subscription_plans
            WHERE is_active = 1
            ORDER BY monthly_price ASC
        """)

        plans = cursor.fetchall()

        return render_template(
            "subscription/renew.html",
            subscription=subscription,
            plans=plans,
            role="clerk",
            active_page="subscription"
        )

    except Exception as e:
        print("RENEW PAGE ERROR:", e)
        return "Renew page failed ❌"

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# =========================================================
# 📄 SAVE CERTIFICATE SETTINGS
# =========================================================
@app.route("/superadmin/settings/certificate", methods=["POST"])
@admin_required
def save_certificate_settings():

    conn = None
    cursor = None

    try:

        # =====================================================
        # GET FORM DATA
        # =====================================================

        tc_prefix = (
            request.form.get(
                "tc_prefix", ""
            ).strip().upper()
        )

        bonafide_prefix = (
            request.form.get(
                "bonafide_prefix", ""
            ).strip().upper()
        )

        auto_numbering = (
            request.form.get(
                "auto_numbering", ""
            ).strip()
        )

        enable_certificate_labels = (
            request.form.get(
                "enable_certificate_labels", ""
            ).strip()
        )

        show_tc_logo = (
            request.form.get(
                "show_tc_logo", ""
                ).strip()
        )

        show_tc_watermark = (
            request.form.get(
                "show_tc_watermark", ""
            ).strip()
        )

        show_bonafide_logo = (
            request.form.get(
                "show_bonafide_logo", ""
            ).strip()
        )

        show_bonafide_watermark = (
            request.form.get(
                "show_bonafide_watermark", ""
            ).strip()
        )


        

        # =====================================================
        # VALIDATION
        # =====================================================

        if not tc_prefix:
            return "TC prefix missing ❌"

        if not bonafide_prefix:
            return "Bonafide prefix missing ❌"

        if auto_numbering not in [
            "Enabled",
            "Disabled"
        ]:
            return "Invalid auto numbering ❌"

        if enable_certificate_labels not in [
            "Enabled",
            "Disabled"
        ]:
            return "Invalid label setting ❌"

        # =====================================================
        # DB CONNECTION
        # =====================================================

        conn = get_connection()
        cursor = conn.cursor()

        # =====================================================
        # CHECK SETTINGS EXISTS
        # =====================================================

        cursor.execute("""
            SELECT id
            FROM system_settings
            WHERE id = 1
        """)

        settings = cursor.fetchone()

        if not settings:
            return "System settings not found ❌"

        # =====================================================
        # UPDATE SETTINGS
        # =====================================================

        cursor.execute("""
            UPDATE system_settings
            SET
                tc_prefix = ?,
                bonafide_prefix = ?,
                       
                auto_numbering = ?,
                enable_certificate_labels = ?,

                show_tc_logo = ?,
                show_tc_watermark = ?,

                show_bonafide_logo = ?,
                show_bonafide_watermark = ?,
                       
                updated_at = GETDATE()
            WHERE id = 1
        """, (

            tc_prefix,
            bonafide_prefix,

            auto_numbering,
            enable_certificate_labels,

            show_tc_logo,
            show_tc_watermark,

            show_bonafide_logo,
            show_bonafide_watermark
        ))

        conn.commit()

        return redirect(
            url_for("superadmin_settings")
        )

    except Exception as e:

        if conn:
            conn.rollback()

        print(
            "❌ CERTIFICATE SETTINGS ERROR:",
            e
        )

        return f"Certificate Settings Error ❌ {e}"

    finally:

        if cursor:
            cursor.close()

        if conn:
            conn.close()
 
# =========================================================
# 🧩 SAVE FEATURE MODULE SETTINGS
# =========================================================
@app.route("/superadmin/settings/modules", methods=["POST"])
@admin_required
def save_feature_module_settings():

    conn = None
    cursor = None

    try:

        conn = get_connection()
        cursor = conn.cursor()

        enable_attendance = request.form.get(
            "enable_attendance", "Disabled"
        )

        enable_fee_management = request.form.get(
            "enable_fee_management", "Disabled"
        )

        enable_teacher_management = request.form.get(
            "enable_teacher_management", "Disabled"
        )

        enable_results = request.form.get(
            "enable_results", "Disabled"
        )

        enable_import_export = request.form.get(
            "enable_import_export", "Disabled"
        )

        enable_timetable = request.form.get(
            "enable_timetable", "Disabled"
        )

        enable_notice_board = request.form.get(
            "enable_notice_board", "Disabled"
        )

        cursor.execute("""
            UPDATE system_settings
            SET

                enable_attendance = ?,
                enable_fee_management = ?,
                enable_teacher_management = ?,
                enable_results = ?,
                enable_import_export = ?,
                enable_timetable = ?,
                enable_notice_board = ?,

                updated_at = GETDATE()

            WHERE id = 1
        """, (

            enable_attendance,
            enable_fee_management,
            enable_teacher_management,
            enable_results,
            enable_import_export,
            enable_timetable,
            enable_notice_board

        ))

        conn.commit()

        return redirect(
            url_for("superadmin_settings")
        )

    except Exception as e:

        if conn:
            conn.rollback()

        print("❌ FEATURE MODULE SETTINGS ERROR:", e)

        return f"Feature Module Error ❌ {e}"

    finally:

        if cursor:
            cursor.close()

        if conn:
            conn.close()

 # =========================================================
# 💳 SAVE PAYMENT SETTINGS
# =========================================================
@app.route(
    "/superadmin/settings/payment",
    methods=["POST"]
)
@admin_required
def save_payment_settings():

    conn = None
    cursor = None

    try:

        # =====================================================
        # GET FORM DATA
        # =====================================================

        payment_gateway = (
            request.form.get(
                "payment_gateway"
            ) or "Razorpay"
        ).strip()

        razorpay_key_id = (
            request.form.get(
                "razorpay_key_id"
            ) or ""
        ).strip()

        razorpay_mode = (
            request.form.get(
                "razorpay_mode"
            ) or "Sandbox"
        ).strip()

        currency = (
            request.form.get(
                "currency"
            ) or "INR"
        ).strip()

        gst_percentage = (
            request.form.get(
                "gst_percentage"
            ) or "0"
        ).strip()

        # =====================================================
        # VALIDATION
        # =====================================================

        allowed_gateways = [

            "Razorpay",
            "Stripe",
            "PayPal",
            "Disabled"

        ]

        if payment_gateway not in allowed_gateways:

            return "Invalid payment gateway ❌"

        allowed_modes = [

            "Sandbox",
            "Live"

        ]

        if razorpay_mode not in allowed_modes:

            return "Invalid payment mode ❌"

        # =====================================================
        # DB CONNECTION
        # =====================================================

        conn = get_connection()
        cursor = conn.cursor()

        # =====================================================
        # UPDATE SYSTEM SETTINGS
        # =====================================================

        cursor.execute("""

            UPDATE system_settings
            SET

                payment_gateway = ?,
                razorpay_key_id = ?,
                razorpay_mode = ?,
                currency = ?,
                gst_percentage = ?,

                updated_at = GETDATE()

            WHERE id = 1

        """, (

            payment_gateway,
            razorpay_key_id,
            razorpay_mode,
            currency,
            gst_percentage

        ))

        conn.commit()

        return redirect(
            url_for("superadmin_settings")
        )

    except Exception as e:

        if conn:
            conn.rollback()

        print(
            "❌ PAYMENT SETTINGS ERROR:",
            e
        )

        return f"Payment Settings Error ❌ {e}"

    finally:

        if cursor:
            cursor.close()

        if conn:
            conn.close()

 # =========================================================
# 📧 SAVE SMTP SETTINGS
# =========================================================
@app.route(
    "/superadmin/settings/smtp",
    methods=["POST"]
)
@admin_required
def save_smtp_settings():

    conn = None
    cursor = None

    try:

        # =========================================
        # GET FORM DATA
        # =========================================

        smtp_email = (
            request.form.get(
                "smtp_email", ""
            ).strip()
        )

        smtp_password = (
            request.form.get(
                "smtp_password", ""
            ).strip()
        )

        smtp_server = (
            request.form.get(
                "smtp_server", ""
            ).strip()
        )

        smtp_port = (
            request.form.get(
                "smtp_port", ""
            ).strip()
        )

        smtp_tls = (
            request.form.get(
                "smtp_tls", ""
            ).strip()
        )

        # =========================================
        # VALIDATION
        # =========================================

        if not smtp_email:
            return "SMTP email missing ❌"

        if not smtp_password:
            return "SMTP password missing ❌"

        if not smtp_server:
            return "SMTP server missing ❌"

        if not smtp_port:
            return "SMTP port missing ❌"

        if smtp_tls not in [
            "Enabled",
            "Disabled"
        ]:
            return "Invalid SMTP TLS ❌"

        # =========================================
        # DB CONNECTION
        # =========================================

        conn = get_connection()
        cursor = conn.cursor()

        # =========================================
        # SETTINGS EXISTS CHECK
        # =========================================

        cursor.execute("""

            SELECT id
            FROM system_settings
            WHERE id = 1

        """)

        settings = cursor.fetchone()

        if not settings:
            return "System settings missing ❌"

        # =========================================
        # UPDATE SETTINGS
        # =========================================

        cursor.execute("""

            UPDATE system_settings
            SET

                smtp_email = ?,
                smtp_password = ?,
                smtp_server = ?,
                smtp_port = ?,
                smtp_tls = ?,

                updated_at = GETDATE()

            WHERE id = 1

        """, (

            smtp_email,
            smtp_password,
            smtp_server,
            smtp_port,
            smtp_tls

        ))

        conn.commit()

        return redirect(
            url_for("superadmin_settings")
        )

    except Exception as e:

        if conn:
            conn.rollback()

        print(
            "❌ SMTP SETTINGS ERROR:",
            e
        )

        return f"SMTP Settings Error ❌ {e}"

    finally:

        if cursor:
            cursor.close()

        if conn:
            conn.close()
 

# =========================================================
# 💾 CREATE REAL DATABASE BACKUP
# =========================================================

@app.route(
    "/superadmin/settings/backup",
    methods=["POST"]
)
@admin_required
def create_backup():

    conn = None
    cursor = None

    try:

        # =========================================
        # DB CONNECTION
        # =========================================

        conn = get_connection()

        # BACKUP DATABASE requires autocommit

        conn.autocommit = True

        cursor = conn.cursor()

        # =========================================
        # ADMIN SESSION
        # =========================================

        admin_id = session.get(
            "admin_user_id"
        )

        if not admin_id:
            return "Admin session missing ❌"

        # =========================================
        # BACKUP DIRECTORY
        # =========================================

        backup_dir = os.path.join(
            os.getcwd(),
            "backups"
        )

        os.makedirs(
            backup_dir,
            exist_ok=True
        )

        # =========================================
        # FILE NAME
        # =========================================

        backup_date = datetime.now()

        backup_file = (
            f"backup_"
            f"{backup_date.strftime('%Y%m%d_%H%M%S')}"
            f".bak"
        )

        backup_path = os.path.join(
            backup_dir,
            backup_file
        )

        # =========================================
        # SQL SERVER BACKUP COMMAND
        # =========================================

        sql = f"""
        BACKUP DATABASE SchoolERP
        TO DISK = '{backup_path}'
        WITH INIT,
        NAME = 'Full Backup of SchoolERP';
        """
        cursor.execute(sql)

      

        # =========================================
        # FILE SIZE
        # =========================================

        size_bytes = os.path.getsize(
            backup_path
        )

        size_mb = round(
            size_bytes / (1024 * 1024),
            2
        )

        backup_size = f"{size_mb} MB"

        # =========================================
        # SAVE BACKUP LOG
        # =========================================

        cursor.execute("""

            INSERT INTO system_backup_logs
            (
                backup_file,
                backup_status,
                backup_size,
                backup_date,
                backup_type,
                created_by
            )

            VALUES (?, ?, ?, ?, ?, ?)

        """, (

            backup_file,
            "Success",
            backup_size,
            backup_date,
            "manual",
            admin_id

        ))

        # =========================================
        # UPDATE SETTINGS
        # =========================================

        cursor.execute("""

            UPDATE system_settings

            SET

                last_backup = ?,
                backup_status = ?,
                updated_at = GETDATE()

            WHERE id = 1

        """, (

            backup_date,
            "Enabled"

        ))

        conn.commit()

        print("✅ REAL BACKUP CREATED")

        return redirect(
            url_for("superadmin_settings")
        )

    except Exception as e:

        if conn:
            conn.rollback()

        print(
            "❌ BACKUP ERROR:",
            e
        )

        return f"Backup Failed ❌ {e}"

    finally:

        if cursor:
            cursor.close()

        if conn:
            conn.close()

 # =========================================================
# 📥 DOWNLOAD BACKUP
# =========================================================

@app.route(
    "/download-backup/<filename>"
)
@admin_required
def download_backup(filename):

    filename = secure_filename(filename)

    backup_path = os.path.join(
        os.getcwd(),
        "backups",
        filename
    )

    if not os.path.exists(
        backup_path
    ):
        return "Backup file not found ❌"

    return send_file(

        backup_path,

        as_attachment=True

    )

# =========================================================
# 🤖 AUTO BACKUP FUNCTION
# =========================================================

def auto_backup():

    conn = None
    cursor = None

    try:

        # =========================================
        # DB CONNECTION
        # =========================================

        conn = get_connection()

        conn.autocommit = True

        cursor = conn.cursor()

        # =========================================
        # BACKUP DIRECTORY
        # =========================================

        backup_dir = os.path.join(
            os.getcwd(),
            "backups"
        )

        os.makedirs(
            backup_dir,
            exist_ok=True
        )

        # =========================================
        # BACKUP FILE NAME
        # =========================================

        backup_date = datetime.now()

        backup_file = (
            f"auto_backup_"
            f"{backup_date.strftime('%Y%m%d_%H%M%S')}"
            f".bak"
        )

        backup_path = os.path.join(
            backup_dir,
            backup_file
        )

        # =========================================
        # SQL SERVER BACKUP
        # =========================================

        sql = f"""

        BACKUP DATABASE SchoolERP

        TO DISK = '{backup_path}'

        WITH INIT,
        NAME = 'Auto Backup';

        """

        cursor.execute(sql)

        # =========================================
        # FILE SIZE
        # =========================================

        size_bytes = os.path.getsize(
            backup_path
        )

        size_mb = round(
            size_bytes / (1024 * 1024),
            2
        )

        backup_size = f"{size_mb} MB"

        # =========================================
        # SAVE BACKUP LOG
        # =========================================

        cursor.execute("""

            INSERT INTO system_backup_logs
            (
                backup_file,
                backup_status,
                backup_size,
                backup_date,
                backup_type,
                created_by
            )

            VALUES (?, ?, ?, ?, ?, ?)

        """, (

            backup_file,
            "Success",
            backup_size,
            backup_date,
            "automatic",
            1

        ))

        # =========================================
        # KEEP ONLY LATEST 10 BACKUPS
        # =========================================

        cursor.execute("""

            SELECT

                id,
                backup_file

            FROM system_backup_logs
                       
            WHERE backup_type = 'automatic'

            ORDER BY backup_date DESC

        """)

        logs = cursor.fetchall()

        # =========================================
        # DELETE OLD BACKUPS
        # =========================================

        if len(logs) > 10:

            old_logs = logs[10:]

            for log in old_logs:

                old_id = log[0]

                old_file = log[1]

                old_path = os.path.join(
                    backup_dir,
                    old_file
                )

                # =================================
                # DELETE FILE
                # =================================

                if os.path.exists(old_path):

                    os.remove(old_path)

                # =================================
                # DELETE DB LOG
                # =================================

                cursor.execute("""

                    DELETE FROM system_backup_logs

                    WHERE id = ?

                """, (

                    old_id,

                ))

        # =========================================
        # SAVE ALL CHANGES
        # =========================================

        conn.commit()

        print("✅ AUTO BACKUP CREATED")

    except Exception as e:

        print(
            "❌ AUTO BACKUP ERROR:",
            e
        )

    finally:

        # =========================================
        # CLOSE DB
        # =========================================

        if cursor:
            cursor.close()

        if conn:
            conn.close()


# =========================================================
# ⏰ AUTO BACKUP SCHEDULER
# =========================================================

scheduler = BackgroundScheduler(
    daemon=True
)

# =========================================================
# TEST MODE
# EVERY 30 SECONDS
# =========================================================

scheduler.add_job(

    func=auto_backup,

    trigger="cron",

    hour=2,
    minute=0

)

# =========================================================
# START SCHEDULER
# =========================================================

if not scheduler.running:
    scheduler.start()

# =========================================================
# 🗑 DELETE BACKUP
# =========================================================

@app.route(
    "/delete-backup/<int:backup_id>"
)
@admin_required
def delete_backup(backup_id):

    conn = None
    cursor = None

    try:

        conn = get_connection()
        cursor = conn.cursor()

        # =========================================
        # GET BACKUP FILE
        # =========================================

        cursor.execute("""

            SELECT backup_file
            FROM system_backup_logs
            WHERE id = ?

        """, (backup_id,))

        backup = cursor.fetchone()

        if not backup:
            return "Backup not found ❌"

        backup_file = backup.backup_file

        # =========================================
        # FILE PATH
        # =========================================

        backup_path = os.path.join(
            os.getcwd(),
            "backups",
            backup_file
        )

        # =========================================
        # DELETE FILE
        # =========================================

        if os.path.exists(backup_path):

            os.remove(backup_path)

        # =========================================
        # DELETE DB LOG
        # =========================================

        cursor.execute("""

            DELETE FROM system_backup_logs
            WHERE id = ?

        """, (backup_id,))

        conn.commit()

        print("✅ BACKUP DELETED")

        return redirect(
            url_for("superadmin_settings")
        )

    except Exception as e:

        if conn:
            conn.rollback()

        print("❌ DELETE BACKUP ERROR:", e)

        return f"Delete Backup Failed ❌ {e}"

    finally:

        if cursor:
            cursor.close()

        if conn:
            conn.close()

 # =========================================================
# ♻ SAFE BACKUP VERIFY RESTORE
# =========================================================

@app.route(
    "/restore-backup/<filename>"
)
@admin_required
def restore_backup(filename):

    filename = secure_filename(filename)

    conn = None
    cursor = None

    try:

        # =========================================
        # BACKUP PATH
        # =========================================

        backup_path = os.path.join(
            os.getcwd(),
            "backups",
            filename
        )

        if not os.path.exists(backup_path):

            return "Backup file not found ❌"
        
        if not filename.endswith(".bak"):
            
            return "Invalid backup file ❌"

        # =========================================
        # CONNECT
        # =========================================

        conn = get_connection()

        conn.autocommit = True

        cursor = conn.cursor()

        # =========================================
        # TEMP DATABASE NAME
        # =========================================

        temp_db = "SchoolERP_TestRestore"

        # =========================================
        # DELETE OLD TEST DB
        # =========================================

        cursor.execute(f"""

        IF DB_ID('{temp_db}') IS NOT NULL
        BEGIN

            ALTER DATABASE [{temp_db}]
            SET SINGLE_USER
            WITH ROLLBACK IMMEDIATE;

            DROP DATABASE [{temp_db}];

        END

        """)

        # =========================================
        # RESTORE TO TEST DATABASE
        # =========================================

        restore_sql = f"""

        RESTORE DATABASE [{temp_db}]

        FROM DISK = '{backup_path}'

        WITH
        MOVE 'SchoolERP'
        TO 'C:\\Program Files\\Microsoft SQL Server\\MSSQL17.SQLEXPRESS\\MSSQL\\DATA\\{temp_db}.mdf',

        MOVE 'SchoolERP_log'
        TO 'C:\\Program Files\\Microsoft SQL Server\\MSSQL17.SQLEXPRESS\\MSSQL\\DATA\\{temp_db}_log.ldf',

        REPLACE

        """

        cursor.execute(restore_sql)

        print("✅ BACKUP VERIFIED SUCCESSFULLY")

        return redirect(
            url_for("superadmin_settings")
        )

    except Exception as e:

        print("❌ RESTORE ERROR:", e)

        return f"Restore Failed ❌ {e}"

    finally:

        if cursor:
            cursor.close()

        if conn:
            conn.close()
            
 # =========================================================
# 🛠 SAVE MAINTENANCE SETTINGS (REALTIME ENTERPRISE)
# =========================================================
@app.route(
    "/superadmin/settings/maintenance",
    methods=["POST"]
)
@admin_required
def save_maintenance_settings():

    conn = None
    cursor = None

    try:

        # =========================================
        # GET FORM DATA
        # =========================================

        maintenance_mode = request.form.get(
            "maintenance_mode",
            ""
        ).strip()

        maintenance_message = request.form.get(
            "maintenance_message",
            ""
        ).strip()

        # =========================================
        # VALIDATION
        # =========================================

        if not maintenance_mode:
            return "Maintenance mode missing ❌"

        if maintenance_mode not in [
            "ON",
            "OFF"
        ]:
            return "Invalid maintenance mode ❌"

        # =========================================
        # DEFAULT MESSAGE
        # =========================================

        if not maintenance_message:

            if maintenance_mode == "ON":

                maintenance_message = (
                    "ERP system is currently "
                    "under maintenance. "
                    "Please try again later."
                )

            else:

                maintenance_message = (
                    "System running normally"
                )

        # =========================================
        # DB CONNECTION
        # =========================================

        conn = get_connection()
        cursor = conn.cursor()

        # =========================================
        # CHECK SETTINGS EXISTS
        # =========================================

        cursor.execute("""

            SELECT id
            FROM system_settings
            WHERE id = 1

        """)

        settings = cursor.fetchone()

        if not settings:
            return "System settings not found ❌"

        # =========================================
        # UPDATE SETTINGS
        # =========================================

        cursor.execute("""

            UPDATE system_settings

            SET

                maintenance_mode = ?,
                maintenance_message = ?,
                updated_at = GETDATE()

            WHERE id = 1

        """, (

            maintenance_mode,
            maintenance_message

        ))

        # =========================================
        # SAVE
        # =========================================

        conn.commit()

        # =========================================
        # TERMINAL LOG
        # =========================================

        print(
            f"✅ MAINTENANCE MODE: "
            f"{maintenance_mode}"
        )

        # =========================================
        # REDIRECT
        # =========================================

        return redirect(
            url_for("superadmin_settings")
        )

    except Exception as e:

        if conn:
            conn.rollback()

        print(
            "❌ MAINTENANCE SETTINGS ERROR:",
            e
        )

        return (
            f"Maintenance Settings Error ❌ {e}"
        )

    finally:

        if cursor:
            cursor.close()

        if conn:
            conn.close()

            # =========================================================
# 🎨 SAVE BRANDING SETTINGS
# =========================================================
@app.route(
    "/superadmin/save-branding-settings",
    methods=["POST"]
)
@admin_required
def save_branding_settings():

    conn = None
    cursor = None

    try:

        # =========================================
        # DB CONNECTION
        # =========================================

        conn = get_connection()
        cursor = conn.cursor()

        # =========================================
        # FORM DATA
        # =========================================

        primary_color = (
            request.form.get("primary_color")
            or "#10b981"
        ).strip()

        secondary_color = (
            request.form.get("secondary_color")
            or "#3b82f6"
        ).strip()

        button_color = (
            request.form.get("button_color")
            or "#111827"
        ).strip()

        erp_version = (
            request.form.get("erp_version")
            or ""
        ).strip()

        footer_text = (
            request.form.get("footer_text")
            or ""
        ).strip()

        powered_by = (
            request.form.get("powered_by")
            or ""
        ).strip()

        website_url = (
            request.form.get("website_url")
            or ""
        ).strip()

        # =========================================
        # FAVICON UPLOAD
        # =========================================

        favicon_filename = None

        favicon = request.files.get("favicon")

        if favicon and favicon.filename:

            filename = secure_filename(
                favicon.filename
            )

            upload_folder = os.path.join(
                "static",
                "uploads",
                "branding"
            )

            os.makedirs(
                upload_folder,
                exist_ok=True
            )

            favicon_path = os.path.join(
                upload_folder,
                filename
            )

            favicon.save(favicon_path)

            favicon_filename = (
                "uploads/branding/" + filename
            )

        # =========================================
        # UPDATE SETTINGS
        # =========================================

        if favicon_filename:

            cursor.execute("""

                UPDATE system_settings
                SET

                    primary_color = ?,
                    secondary_color = ?,
                    button_color = ?,

                    erp_version = ?,
                    footer_text = ?,
                    powered_by = ?,
                    website_url = ?,

                    favicon = ?,

                    updated_at = GETDATE()

                WHERE id = 1

            """, (

                primary_color,
                secondary_color,
                button_color,

                erp_version,
                footer_text,
                powered_by,
                website_url,

                favicon_filename

            ))

        else:

            cursor.execute("""

                UPDATE system_settings
                SET

                    primary_color = ?,
                    secondary_color = ?,
                    button_color = ?,

                    erp_version = ?,
                    footer_text = ?,
                    powered_by = ?,
                    website_url = ?,

                    updated_at = GETDATE()

                WHERE id = 1

            """, (

                primary_color,
                secondary_color,
                button_color,

                erp_version,
                footer_text,
                powered_by,
                website_url

            ))

        # =========================================
        # SAVE
        # =========================================

        conn.commit()

        return redirect(
            url_for("superadmin_settings")
        )

    except Exception as e:

        if conn:
            conn.rollback()

        print(
            "❌ BRANDING SETTINGS ERROR:",
            e
        )

        return f"""

        <h2>
            Branding Settings Error ❌
        </h2>

        <p>{e}</p>

        """

    finally:

        if cursor:
            cursor.close()

        if conn:
            conn.close()


 # =========================================================
# 💰 PAYMENT PAGE
# =========================================================
@app.route("/clerk/subscription/payment", methods=["POST"])
@login_required
def subscription_payment():

    subscription_id = request.form.get("subscription_id")
    plan_id = request.form.get("plan_id")

    if not subscription_id or not plan_id:
        return "Subscription missing ❌"

    conn = None
    cursor = None

    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                id,
                plan_name,
                monthly_price
            FROM subscription_plans
            WHERE id = ?
        """, (plan_id,))

        plan = cursor.fetchone()

        if not plan:
            return "Plan not found ❌"

         # Razorpay client
        client = razorpay.Client(
            auth=(
                RAZORPAY_KEY_ID,
                RAZORPAY_KEY_SECRET
            )
        )

        amount_in_paise = int(float(plan[2]) * 100)

        # Create order
        razorpay_order = client.order.create({
            "amount": amount_in_paise,
            "currency": "INR",
            "payment_capture": 1
        })

        return render_template(
            "subscription/payment.html",
            subscription_id=subscription_id,
            plan_id=plan[0],
            plan_name=plan[1],
            amount=plan[2],
            razorpay_order_id=razorpay_order["id"],
            razorpay_key=RAZORPAY_KEY_ID
        )

    except Exception as e:
        print("PAYMENT PAGE ERROR:", e)
        return f"Payment page failed ❌ {e}"

    finally:
        if cursor:
            cursor.close()

        if conn:
            conn.close()

# =========================================================
# ✅ PAYMENT SUCCESS
# =========================================================
@app.route("/clerk/subscription/payment-success", methods=["POST"])
@login_required
def payment_success():

    school_id = session.get("clerk_school_id")

    plan_id = request.form.get(
        "plan_id"
    )

    subscription_id = request.form.get(
        "subscription_id"
    )

    razorpay_payment_id = request.form.get(
        "razorpay_payment_id"
    )

    razorpay_order_id = request.form.get(
        "razorpay_order_id"
    )

    razorpay_signature = request.form.get(
        "razorpay_signature"
    )

    conn = None
    cursor = None

    try:

        # =====================================================
        # VALIDATION
        # =====================================================

        if not school_id:
            return "School session missing ❌"

        if not plan_id:
            return "Plan missing ❌"

        if not subscription_id:
            return "Subscription missing ❌"

        # =====================================================
        # DB CONNECTION
        # =====================================================

        conn = get_connection()
        cursor = conn.cursor()

        # =====================================================
        # PREVENT DUPLICATE PAYMENT
        # =====================================================

        cursor.execute("""

            SELECT id
            FROM payment_logs
            WHERE order_id = ?

        """, (razorpay_order_id,))

        existing_order = cursor.fetchone()

        if existing_order:

            return "Payment already processed "

        # =====================================================
        # VERIFY SIGNATURE
        # =====================================================

        client = razorpay.Client(
            auth=(
                RAZORPAY_KEY_ID,
                RAZORPAY_KEY_SECRET
            )
        )

        verify_data = {

            "razorpay_order_id":
            razorpay_order_id,

            "razorpay_payment_id":
            razorpay_payment_id,

            "razorpay_signature":
            razorpay_signature

        }

        try:

            client.utility.verify_payment_signature(
                verify_data
            )

        except Exception as verify_error:

            # =================================================
            # SAVE FAILED PAYMENT
            # =================================================

            cursor.execute("""

                INSERT INTO payment_logs (

                    school_id,
                    subscription_id,
                    plan_id,
                    amount,

                    payment_status,
                    payment_id,
                    order_id,

                    transaction_type,
                    payment_gateway,
                    failure_reason

                )

                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)

            """, (

                school_id,
                subscription_id,
                plan_id,
                0,

                "failed",
                razorpay_payment_id,
                razorpay_order_id,

                "Subscription Renewal",
                "Razorpay",
                str(verify_error)

            ))

            conn.commit()

            return (
                f"Payment verification failed ❌ "
                f"{verify_error}"
            )

        # =====================================================
        # GET PLAN DETAILS
        # =====================================================

        cursor.execute("""
            SELECT

                plan_name,
                monthly_price,
                duration_months

            FROM subscription_plans
            WHERE id = ?

        """, (plan_id,))

        plan = cursor.fetchone()

        if not plan:
            return "Plan not found ❌"

        if plan[2] is None:
            return "Plan duration missing ❌"

        # =====================================================
        # GET SCHOOL DETAILS
        # =====================================================

        cursor.execute("""
            SELECT
                name,
                email
            FROM schools
            WHERE school_id = ?
        """, (school_id,))

        school = cursor.fetchone()

        if not school:
            return "School not found ❌"

        school_name = school[0]
        school_email = school[1]

        # =====================================================
        # UPDATE SUBSCRIPTION
        # =====================================================

        cursor.execute("""
            UPDATE subscriptions
            SET

                plan_id = ?,
                plan_name = ?,
                amount = ?,

                start_date = GETDATE(),

                end_date = DATEADD(
                    MONTH,
                    ?,
                    GETDATE()
                ),

                status = 'active'

            WHERE school_id = ?
            AND id = ?

        """, (

            int(plan_id),
            plan[0],
            plan[1],
            int(plan[2]),

            school_id,
            subscription_id

        ))

        # =====================================================
        # PAYMENT LOG
        # =====================================================

        cursor.execute("""
            INSERT INTO payment_logs (

                school_id,
                subscription_id,
                plan_id,
                amount,

                payment_status,
                payment_id,
                order_id,

                transaction_type,
                payment_gateway

            )

            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)

        """, (

            school_id,
            subscription_id,
            plan_id,
            plan[1],

            "success",
            razorpay_payment_id,
            razorpay_order_id,

            "Subscription Renewal",
            "Razorpay"

        ))

        # =====================================================
        # SAVE CHANGES
        # =====================================================

        conn.commit()

        # =====================================================
        # SEND PAYMENT RECEIPT EMAIL
        # =====================================================

        try:

            subject = (
                "Payment Successful - "
                "ShalaSync ERP"
            )

            body = f"""

            <div style="font-family:Arial;padding:20px;">

                <h2 style="color:#10b981;">
                    Payment Successful
                </h2>

                <p>
                    Dear {school_name},
                </p>

                <p>
                    Your subscription payment
                    was completed successfully.
                </p>

                <hr>

                <p>
                    <b>Plan:</b>
                    {plan[0]}
                </p>

                <p>
                    <b>Amount Paid:</b>
                    Rs. {plan[1]}
                </p>

                <p>
                    <b>Payment ID:</b>
                    {razorpay_payment_id}
                </p>

                <p>
                    <b>Order ID:</b>
                    {razorpay_order_id}
                </p>

                <p>
                    <b>Duration:</b>
                    {plan[2]} Month(s)
                </p>

                <p>
                    <b>Status:</b>
                    Success
                </p>

                <hr>

                <p>
                    Thank you for renewing
                    your ShalaSync ERP subscription.
                </p>

            </div>

            """

            email_result = send_email(

                school_email,
                subject,
                body

            )

            if email_result == True:

                print(
                    "✅ PAYMENT RECEIPT EMAIL SENT"
                )

            else:

                print(
                    "❌ PAYMENT EMAIL FAILED:",
                    email_result
                )
                
        except Exception as email_error:

            print(
                "PAYMENT EMAIL ERROR:",
                email_error
            )

        # =====================================================
        # REDIRECT
        # =====================================================

        return redirect(
            url_for("clerk_dashboard")
        )

    except Exception as e:

        if conn:
            conn.rollback()

        print(
            "PAYMENT VERIFY ERROR:",
            e
        )

        return (
            f"Payment verification failed ❌ "
            f"{e}"
        )

    finally:

        if cursor:
            cursor.close()

        if conn:
            conn.close()

# =============================================================================================



# =========================================================
# 🏫 CLERK DASHBOARD (REAL-TIME + CLEAN)
# =========================================================
@app.route("/clerk/dashboard")
@login_required
def clerk_dashboard():

    conn = None
    cursor = None

    try:

        conn = get_connection()
        cursor = conn.cursor()

        school_id = session.get("clerk_school_id")

        # =====================================================
        # SESSION SAFETY
        # =====================================================

        if not school_id:
            return "School session missing ❌"

        # =====================================================
        # 📧 SUBSCRIPTION AUTO CHECK + REMINDER EMAIL
        # =====================================================

        cursor.execute("""
            SELECT TOP 1
                id,
                end_date,
                status
            FROM subscriptions
            WHERE school_id = ?
            ORDER BY id DESC
        """, (school_id,))

        sub = cursor.fetchone()

        if sub:

            subscription_id = sub[0]
            end_date = sub[1]
            current_status = sub[2]

            # =========================================
            # CONVERT SQL DATETIME TO DATE
            # =========================================

            if end_date and isinstance(end_date, datetime):
                end_date = end_date.date()

            # =========================================
            # GET SYSTEM GRACE PERIOD
            # =========================================

            cursor.execute("""
                SELECT TOP 1
                    grace_period
                FROM system_settings
                WHERE id = 1
            """)

            settings = cursor.fetchone()

            grace_days = 0

            if settings and settings[0]:
                grace_days = int(settings[0])

            # =========================================
            # FINAL GRACE DATE
            # =========================================

            grace_end_date = None
            if end_date:
                grace_end_date = end_date + timedelta(days=grace_days)

            # =====================================================
            # 📧 SUBSCRIPTION REMINDER EMAIL SYSTEM
            # =====================================================

            if end_date:

                today_date = datetime.now().date()

                remaining_days = (
                    end_date - today_date
                ).days

                print("Remaining Days:", remaining_days)

                email_type = None

                # =========================================
                # DEFINE EMAIL TYPE
                # =========================================

                if remaining_days == 7:
                    email_type = "7_days_warning"

                elif remaining_days == 3:
                    email_type = "3_days_warning"

                elif remaining_days == 1:
                    email_type = "1_day_warning"

                elif remaining_days == 0:
                    email_type = "expiry_today"

                print("Email Type:", email_type)

                # =========================================
                # SEND EMAIL ONLY IF TYPE EXISTS
                # =========================================

                if email_type:

                    cursor.execute("""

                        SELECT id
                        FROM subscription_email_logs
                        WHERE school_id = ?
                        AND subscription_id = ?
                        AND email_type = ?

                    """, (

                        school_id,
                        subscription_id,
                        email_type

                    ))

                    already_sent = cursor.fetchone()

                    print("Already Sent:", already_sent)

                    # =====================================
                    # SEND ONLY ONCE
                    # =====================================

                    if already_sent is None:

                        # =====================================
                        # GET SCHOOL EMAIL
                        # =====================================

                        cursor.execute("""

                            SELECT
                                name,
                                email
                            FROM schools
                            WHERE school_id = ?

                        """, (school_id,))

                        school_data = cursor.fetchone()

                        print("School Data:", school_data)

                        if school_data:

                            school_name_email = school_data[0]
                            school_email = school_data[1]

                            # =====================================
                            # EMAIL SUBJECT
                            # =====================================

                            subject = (
                                "Subscription Reminder - ShalaSync ERP"
                            )

                            # =====================================
                            # EMAIL BODY
                            # =====================================

                            body = f"""

                            <div style="font-family:Arial;padding:20px;">

                                <h2 style="color:#f59e0b;">
                                    Subscription Expiry Reminder
                                </h2>

                                <p>
                                    Dear {school_name_email},
                                </p>

                                <p>
                                    Your subscription will expire in
                                    <b>{remaining_days} day(s)</b>.
                                </p>

                                <hr>

                                <p>
                                    Please renew your subscription
                                    to continue using ERP services.
                                </p>

                                <p>
                                    Login to dashboard and renew now.
                                </p>

                                <hr>

                                <p>
                                    Thank you,
                                    <br>
                                    <b>ShalaSync ERP Team</b>
                                </p>

                            </div>

                            """

                            # =====================================
                            # SEND EMAIL
                            # =====================================

                            email_sent = send_email(

                                school_email,
                                subject,
                                body

                            )

                            print(
                                "Email Sent Result:",
                                email_sent
                            )

                            # =====================================
                            # SAVE EMAIL LOG
                            # =====================================

                            if email_sent == True:

                                 # FINAL SAFETY CHECK
                                cursor.execute("""

                                    SELECT id
                                    FROM subscription_email_logs
                                    WHERE school_id = ?
                                    AND subscription_id = ?
                                    AND email_type = ?

                                """, (

                                    school_id,
                                    subscription_id,
                                    email_type

                                ))

                                double_check = cursor.fetchone()

                                if double_check is None:
                                    cursor.execute("""

                                    INSERT INTO subscription_email_logs
                                    (
                                        school_id,
                                        subscription_id,
                                        email_type,
                                        sent_at
                                    )
                                    VALUES (?, ?, ?, GETDATE())

                                """, (

                                    school_id,
                                    subscription_id,
                                    email_type

                                ))

                                conn.commit()

                                print(
                                    "✅ SUBSCRIPTION REMINDER EMAIL SENT"
                                )
    

            # =====================================================
            # AUTO EXPIRE SUBSCRIPTION
            # =====================================================

            if (
                grace_end_date
                and datetime.now().date() > grace_end_date
                and current_status == "active"
            ):

                cursor.execute("""
                    UPDATE subscriptions
                    SET status = 'expired'
                    WHERE id = ?
                """, (subscription_id,))

                conn.commit()

                print(
                    "✅ SUBSCRIPTION EXPIRED"
                )

        # =====================================================
        # SCHOOL DATA
        # =====================================================

        cursor.execute("""
            SELECT name
            FROM schools
            WHERE school_id = ?
        """, (school_id,))

        school = cursor.fetchone()

        if not school:
            return "School not found ❌"

        school_name = school[0]

        # =====================================================
        # TOTAL COUNTS
        # =====================================================

        cursor.execute("""
            SELECT COUNT(*)
            FROM students
            WHERE school_id = ?
        """, (school_id,))

        total_students = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(*)
            FROM tc
            WHERE school_id = ?
        """, (school_id,))

        total_tc = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(*)
            FROM bonafide
            WHERE school_id = ?
        """, (school_id,))

        total_bonafide = cursor.fetchone()[0]

        # =====================================================
        # TODAY COUNTS
        # =====================================================

        today = datetime.now().date()

        cursor.execute("""
            SELECT COUNT(*)
            FROM students
            WHERE school_id = ?
            AND CAST(created_at AS DATE) = ?
        """, (school_id, today))

        today_students = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(*)
            FROM tc
            WHERE school_id = ?
            AND CAST(tc_date AS DATE) = ?
        """, (school_id, today))

        today_tc = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(*)
            FROM bonafide
            WHERE school_id = ?
            AND CAST(date AS DATE) = ?
        """, (school_id, today))

        today_bonafide = cursor.fetchone()[0]

        # =====================================================
        # STUDENT GROWTH
        # =====================================================

        cursor.execute("""
            SELECT TOP 5
                YEAR(created_at) AS y,
                MONTH(created_at) AS m,
                COUNT(*) AS total
            FROM students
            WHERE school_id = ?
            GROUP BY YEAR(created_at), MONTH(created_at)
            ORDER BY y DESC, m DESC
        """, (school_id,))

        rows = cursor.fetchall()

        monthly_counts = [row[2] for row in rows][::-1]

        if not monthly_counts:
            monthly_counts = [0]

        growth_data = []

        running_total = 0

        for count in monthly_counts:

            running_total += count

            growth_data.append(
                running_total
            )

        while len(growth_data) < 5:
            growth_data.insert(0, 0)

        # =====================================================
        # TC DATA
        # =====================================================

        cursor.execute("""
            SELECT TOP 5
                CAST(tc_date AS DATE) AS d,
                COUNT(*) AS c
            FROM tc
            WHERE school_id = ?
            GROUP BY CAST(tc_date AS DATE)
            ORDER BY d DESC
        """, (school_id,))

        rows = cursor.fetchall()

        tc_data = [row[1] for row in rows][::-1]

        if len(tc_data) < 5:
            tc_data = [0] * (5 - len(tc_data)) + tc_data

        # =====================================================
        # BONAFIDE DATA
        # =====================================================

        cursor.execute("""
            SELECT COUNT(*)
            FROM bonafide
            WHERE school_id = ?
        """, (school_id,))

        bon_count = cursor.fetchone()[0]

        remaining_students = max(
            0,
            total_students - bon_count
        )

        bonafide_data = [
            bon_count,
            remaining_students
        ]

        # =====================================================
        # GROWTH %
        # =====================================================

        if len(growth_data) >= 2:

            prev = growth_data[-2]
            curr = growth_data[-1]

            growth_percent = min(
                100,
                max(0, curr - prev)
            )

        else:

            growth_percent = min(
                100,
                total_students
            )

        # =====================================================
        # USER PROFILE
        # =====================================================

        cursor.execute("""
            SELECT TOP 1
                u.id,
                u.name,
                u.email,
                u.phone,
                u.address,
                u.designation,
                s.name AS school_name,
                sub.plan_name,
                CASE
                    WHEN sub.end_date IS NULL THEN 0
                    WHEN DATEDIFF(DAY, GETDATE(), sub.end_date) < 0 THEN 0
                    ELSE DATEDIFF(DAY, GETDATE(), sub.end_date)
                END AS remaining_days
            FROM users u
            JOIN schools s
                ON u.school_id = s.school_id
            LEFT JOIN (
                SELECT school_id, plan_name, end_date
                FROM subscriptions
                WHERE status IN ('active','expired')
            ) sub
                ON sub.school_id = s.school_id
            WHERE u.id = ?
        """, (session.get("clerk_user_id"),))

        row = cursor.fetchone()

        if row:

            columns = [
                col[0]
                for col in cursor.description
            ]

            user_profile = dict(
                zip(columns, row)
            )

        else:

            user_profile = {}

        # =====================================================
        # SUBSCRIPTION ALERT SYSTEM
        # =====================================================

        subscription_alert = None

        remaining_days = user_profile.get(
            "remaining_days",
            0
        )

        if remaining_days <= 0:

            subscription_alert = {
                "type": "danger",
                "message": "Your subscription has expired. Please renew now."
            }

        elif remaining_days <= 2:

            subscription_alert = {
                "type": "danger",
                "message": f"Your subscription will expire in {remaining_days} day(s). Renew immediately."
            }

        elif remaining_days <= 7:

            subscription_alert = {
                "type": "warning",
                "message": f"Your subscription will expire in {remaining_days} day(s). Please renew soon."
            }

        elif remaining_days <= 30:

            subscription_alert = {
                "type": "info",
                "message": f"Your subscription will expire in {remaining_days} days."
            }

        # =====================================================
        # RECENT ACTIVITIES
        # =====================================================

        activities = []

        # ================= STUDENTS =================

        cursor.execute("""
            SELECT TOP 2
                name,
                created_at
            FROM students
            WHERE school_id = ?
            ORDER BY created_at DESC
        """, (school_id,))

        for s in cursor.fetchall():

            activities.append({

                "type": "teal",

                "title": (
                    f"New student admission: {s[0]}"
                ),

                "title_mr": "नवीन विद्यार्थी प्रवेश",

                "time": "Recently"

            })

        # ================= TC =================

        cursor.execute("""
            SELECT TOP 2
                tc.tc_number,
                st.name
            FROM tc
            JOIN students st
                ON tc.student_id = st.id
            WHERE tc.school_id = ?
            ORDER BY tc.tc_date DESC
        """, (school_id,))

        for tc in cursor.fetchall():

            activities.append({

                "type": "orange",

                "title": (
                    f"TC issued for {tc[1]} "
                    f"(TC No: {tc[0]})"
                ),

                "title_mr": "टीसी जारी केले",

                "time": "Recently"

            })

        # ================= BONAFIDE =================

        cursor.execute("""
            SELECT TOP 2
                st.name
            FROM bonafide b
            JOIN students st
                ON b.student_id = st.id
            WHERE b.school_id = ?
            ORDER BY b.date DESC
        """, (school_id,))

        for b in cursor.fetchall():

            activities.append({

                "type": "blue",

                "title": (
                    f"Bonafide certificate issued "
                    f"for {b[0]}"
                ),

                "title_mr": "बोनाफाईड प्रमाणपत्र जारी केले",

                "time": "Recently"

            })

        activities = activities[::-1]

        # =====================================================
        # FINAL RENDER
        # =====================================================

        return render_template(

            "dashboard/clerk.html",

            role="clerk",

            school_name=school_name,

            active_page="dashboard",

            user_profile=user_profile,

            total_students=total_students,

            total_tc=total_tc,

            total_bonafide=total_bonafide,

            today_students=today_students,

            today_tc=today_tc,

            today_bonafide=today_bonafide,

            growth_data=growth_data,

            tc_data=tc_data,

            bonafide_data=bonafide_data,

            growth_percent=growth_percent,

            activities=activities,

            subscription_alert=subscription_alert

        )

    except Exception as e:

        print("❌ DASHBOARD ERROR:", e)

        return f"Dashboard Error ❌ {e}"

    finally:

        if cursor:
            cursor.close()

        if conn:
            conn.close()

# =========================================================
# UPDATE USER PROFILE
# =========================================================

@app.route("/clerk/profile/update", methods=["POST"])
@login_required
def clerk_profile_update():

    conn = None
    cursor = None

    try:
        user_id = session.get("clerk_user_id")

        if not user_id:
            return {
                "status":"error",
                "message":"Session expired"
            }

        name = request.form.get("name","").strip()
        phone = request.form.get("phone","").strip()
        address = request.form.get("address","").strip()
        designation = request.form.get("designation","").strip()

        if not name:
            return {
                "status":"error",
                "message":"Name required"
            }
        
        if phone and (not phone.isdigit() or len(phone) != 10):
            return {
                "status":"error",
                "message":"Invalid phone number"
            }

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE users
            SET
                name=?,
                phone=?,
                address=?,
                designation=?,
                updated_at=GETDATE()
            WHERE id=?
        """,(
            name,
            phone,
            address,
            designation,
            user_id
        ))

        conn.commit()

        return {
            "status":"success",
            "message":"Profile updated successfully"
        }

    except Exception as e:
        return {
            "status":"error",
            "message":str(e)
        }

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# =========================================================
# 🔐 SEND PASSWORD RESET OTP
# PURPOSE:
# Send OTP to registered email
# Store OTP in DB
# OTP valid for 5 minutes
# =========================================================

@app.route(
    "/clerk/profile/send-otp",
    methods=["POST"]
)
@login_required
def clerk_send_password_otp():

    conn = None
    cursor = None

    try:

        # =========================================
        # GET REQUEST DATA
        # =========================================

        data = request.get_json() or {}

        email = (
            data.get("email") or ""
        ).strip()

        if not email:

            return jsonify({

                "status": "error",
                "message": "Email required"

            })

        # =========================================
        # SESSION USER
        # =========================================

        user_id = session.get(
            "clerk_user_id"
        )

        if not user_id:

            return jsonify({

                "status": "error",
                "message": "User session missing"

            })

        # =========================================
        # DB CONNECTION
        # =========================================

        conn = get_connection()
        cursor = conn.cursor()

        # =========================================
        # CHECK USER EMAIL
        # =========================================

        cursor.execute("""

            SELECT
                email,
                name

            FROM users

            WHERE id = ?

        """, (user_id,))

        user = cursor.fetchone()

        if not user:

            return jsonify({

                "status": "error",
                "message": "User not found"

            })

        db_email = (user[0] or "").strip()
        user_name = user[1] or "User"

        # =========================================
        # SECURITY EMAIL MATCH
        # =========================================

        if email.lower() != db_email.lower():

            return jsonify({

                "status": "error",
                "message":
                "Email does not match registered email"

            })

        # =========================================
        # REMOVE OLD UNUSED OTP
        # =========================================

        cursor.execute("""

            DELETE FROM password_reset_otp

            WHERE user_id = ?
            AND is_used = 0

        """, (user_id,))

        # =========================================
        # GENERATE OTP
        # =========================================

        otp = str(

            random.randint(
                100000,
                999999
            )

        )

        expiry_time = (

            datetime.now()
            + timedelta(minutes=5)

        )

        # =========================================
        # SAVE OTP IN DATABASE
        # =========================================

        cursor.execute("""

            INSERT INTO password_reset_otp (

                user_id,
                email,
                otp,
                expires_at,
                is_used,
                attempts,
                created_at

            )

            VALUES (?, ?, ?, ?, ?, ?, GETDATE())

        """, (

            user_id,
            email,
            otp,
            expiry_time,
            0,
            0

        ))

        conn.commit()

        # =========================================
        # TEMP SESSION SUPPORT
        # (REMOVE LATER)
        # =========================================

        session["otp_verified"] = False

        # =========================================
        # SEND EMAIL
        # =========================================

        try:

            msg = Message(

                subject="Password Reset OTP",

                recipients=[email]

            )

            msg.body = f"""

Hello {user_name},

Your OTP for password reset is:

{otp}

This OTP is valid for 5 minutes.

Do not share this OTP with anyone.

Regards,
ShalaSync ERP

            """

            mail.send(msg)

        except Exception as mail_error:

            print(
                "MAIL SEND ERROR:",
                mail_error
            )

            return jsonify({

                "status": "error",

                "message":
                "Failed to send OTP email"

            })

        # =========================================
        # SUCCESS RESPONSE
        # =========================================

        return jsonify({

            "status": "success",

            "message":
            "OTP sent successfully"

        })

    except Exception as e:

        if conn:
            conn.rollback()

        print(
            "SEND OTP ERROR:",
            e
        )

        return jsonify({

            "status": "error",
            "message": str(e)

        })

    finally:

        if cursor:
            cursor.close()

        if conn:
            conn.close()
 
# =========================================================
# ✅ VERIFY OTP
# PURPOSE:
# Verify OTP from database
# =========================================================

@app.route(
    "/clerk/profile/check-otp",
    methods=["POST"]
)
@login_required
def clerk_check_password_otp():

    conn = None
    cursor = None

    try:

        # =========================================
        # GET REQUEST DATA
        # =========================================

        data = request.get_json() or {}

        entered_otp = (
            data.get("otp") or ""
        ).strip()

        # =========================================
        # VALIDATION
        # =========================================

        if not entered_otp:

            return jsonify({

                "status": "error",
                "message": "OTP required"

            })

        if (
            not entered_otp.isdigit()
            or len(entered_otp) != 6
        ):

            return jsonify({

                "status": "error",
                "message": "Invalid OTP format"

            })

        # =========================================
        # SESSION USER
        # =========================================

        user_id = session.get(
            "clerk_user_id"
        )

        if not user_id:

            return jsonify({

                "status": "error",
                "message": "User session missing"

            })

        # =========================================
        # DB CONNECTION
        # =========================================

        conn = get_connection()
        cursor = conn.cursor()

        # =========================================
        # GET LATEST UNUSED OTP
        # =========================================

        cursor.execute("""

            SELECT TOP 1

                id,
                otp,
                expires_at,
                attempts,
                is_used

            FROM password_reset_otp

            WHERE user_id = ?
            AND is_used = 0

            ORDER BY id DESC

        """, (user_id,))

        otp_row = cursor.fetchone()

        # =========================================
        # OTP NOT FOUND
        # =========================================

        if not otp_row:

            return jsonify({

                "status": "error",
                "message": "OTP not found"

            })

        otp_id = otp_row[0]
        saved_otp = otp_row[1]
        expiry_time = otp_row[2]
        attempts = otp_row[3] or 0
        is_used = otp_row[4]

        # =========================================
        # ALREADY USED
        # =========================================

        if is_used == 1:

            return jsonify({

                "status": "error",
                "message": "OTP already used"

            })

        # =========================================
        # BLOCK AFTER 5 ATTEMPTS
        # =========================================

        if attempts >= 5:

            return jsonify({

                "status": "error",

                "message":
                "Too many invalid attempts"

            })

        # =========================================
        # CHECK EXPIRY
        # =========================================

        if datetime.now() > expiry_time:

            return jsonify({

                "status": "error",
                "message": "OTP expired"

            })

        # =========================================
        # INVALID OTP
        # =========================================

        if entered_otp != saved_otp:

            cursor.execute("""

                UPDATE password_reset_otp

                SET attempts = attempts + 1

                WHERE id = ?

            """, (otp_id,))

            conn.commit()

            return jsonify({

                "status": "error",
                "message": "Invalid OTP"

            })

        # =========================================
        # OTP VERIFIED
        # =========================================

        cursor.execute("""

            UPDATE password_reset_otp

            SET

                is_used = 1,
                verified_at = GETDATE()

            WHERE id = ?

        """, (otp_id,))

        conn.commit()

        # =========================================
        # SESSION VERIFIED
        # =========================================

        session["otp_verified"] = True

        # =========================================
        # SUCCESS
        # =========================================

        return jsonify({

            "status": "success",
            "message": "OTP Verified"

        })

    except Exception as e:

        print(
            "VERIFY OTP ERROR:",
            e
        )

        return jsonify({

            "status": "error",
            "message": str(e)

        })

    finally:

        if cursor:
            cursor.close()

        if conn:
            conn.close()
    
 
# =========================================================
# 🔒 UPDATE PASSWORD
# PURPOSE:
# Final password update after OTP verification
# =========================================================

@app.route(
    "/clerk/profile/update-password",
    methods=["POST"]
)
@login_required
def clerk_update_password():

    conn = None
    cursor = None

    try:

        # =========================================
        # SESSION USER
        # =========================================

        user_id = session.get(
            "clerk_user_id"
        )

        if not user_id:

            return jsonify({

                "status": "error",
                "message": "User session missing"

            })

        # =========================================
        # GET REQUEST DATA
        # =========================================

        data = request.get_json() or {}

        new_password = (
            data.get("password") or ""
        ).strip()

        # =========================================
        # PASSWORD REQUIRED
        # =========================================

        if not new_password:

            return jsonify({

                "status": "error",
                "message": "Password required"

            })

        # =========================================
        # STRONG PASSWORD VALIDATION
        # =========================================

        if (

            len(new_password) < 8
            or not any(
                c.isupper()
                for c in new_password
            )
            or not any(
                c.islower()
                for c in new_password
            )
            or not any(
                c.isdigit()
                for c in new_password
            )
            or not any(
                not c.isalnum()
                for c in new_password
            )

        ):

            return jsonify({

                "status": "error",

                "message":
                "Password must contain uppercase, lowercase, number and special character"

            })

        # =========================================
        # DB CONNECTION
        # =========================================

        conn = get_connection()
        cursor = conn.cursor()

        # =========================================
        # CHECK VERIFIED OTP
        # =========================================

        cursor.execute("""

            SELECT TOP 1

                id,
                verified_at

            FROM password_reset_otp

            WHERE user_id = ?
            AND is_used = 1

            ORDER BY id DESC

        """, (user_id,))

        otp_row = cursor.fetchone()

        if not otp_row:

            return jsonify({

                "status": "error",

                "message":
                "OTP verification required"

            })

        verified_time = otp_row[1]

        # =========================================
        # OTP TIME LIMIT AFTER VERIFY
        # OPTIONAL SECURITY
        # =========================================

        if verified_time:

            minutes_passed = (

                datetime.now()
                - verified_time

            ).total_seconds() / 60

            if minutes_passed > 10:

                return jsonify({

                    "status": "error",

                    "message":
                    "OTP verification expired"

                })

        # =========================================
        # HASH PASSWORD
        # =========================================

        hashed_password = (

            bcrypt
            .generate_password_hash(
                new_password
            )
            .decode("utf-8")

        )

        # =========================================
        # UPDATE USER PASSWORD
        # =========================================

        cursor.execute("""

            UPDATE users

            SET

                password = ?,
                last_password_change = GETDATE(),
                updated_at = GETDATE()

            WHERE id = ?

        """, (

            hashed_password,
            user_id

        ))

        # =========================================
        # CLEAN OLD OTP RECORDS
        # =========================================

        cursor.execute("""

            DELETE FROM password_reset_otp

            WHERE user_id = ?

        """, (user_id,))

        conn.commit()

        # =========================================
        # CLEAR SESSION
        # =========================================

        session.pop(
            "otp_verified",
            None
        )

        # =========================================
        # SUCCESS
        # =========================================

        return jsonify({

            "status": "success",

            "message":
            "Password updated successfully"

        })

    except Exception as e:

        if conn:
            conn.rollback()

        print(
            "UPDATE PASSWORD ERROR:",
            e
        )

        return jsonify({

            "status": "error",
            "message": str(e)

        })

    finally:

        if cursor:
            cursor.close()

        if conn:
            conn.close()


    
# =========================================================
# 🎓 AUTO GENERATE ADMISSION NUMBER (ATOMIC + SAFE)
# =========================================================
def generate_admission_no(school_id):

    school_code = get_school_code(school_id)

    conn = get_connection()
    cursor = conn.cursor()

    # ================= ATOMIC UPDATE =================
    cursor.execute("""
        UPDATE school_sequences
        SET admission_last_number = admission_last_number + 1
        OUTPUT inserted.admission_last_number
        WHERE school_id = ?
    """, (school_id,))

    row = cursor.fetchone()

    if not row:
        cursor.close()
        conn.close()
        raise Exception("School sequence not found ❌")

    next_number = row[0]

    conn.commit()

    cursor.close()
    conn.close()

    return f"{school_code}-ADM-{str(next_number).zfill(4)}"

# =========================================================
# ➕ ADD STUDENT (DB VERSION - SAFE)
# =========================================================
@app.route("/clerk/add-student", methods=["GET", "POST"])
@login_required
def add_student():

    school_id = session.get("clerk_school_id")

    # SHOW PREVIEW ONLY (NO SEQUENCE CONSUME)
    next_admission = "Auto Generated On Save"

    if request.method == "POST":

        conn = None
        cursor = None

        try:
            conn = get_connection()
            cursor = conn.cursor()

             #  GET SCHOOL ID
            school_id = session.get("clerk_school_id")

            if not school_id:
                return "School session missing ❌"

            # ================= GET DATA =================
            school_register_no = request.form.get("school_register_no", "").strip()
            name = request.form.get("name", "").strip()
            father_name = request.form.get("father_name", "").strip()
            mother_name = request.form.get("mother_name", "").strip()
            student_uid = request.form.get("student_uid", "").strip()
            aadhaar = request.form.get("aadhaar", "").strip()
            apaar_id = request.form.get("apaar_id", "").strip()

            dob = parse_date(request.form.get("dob"))
            birth_place = request.form.get("birth_place").strip()
            nationality = request.form.get("nationality").strip()
            mother_tongue = request.form.get("mother_tongue").strip()
            religion = request.form.get("religion").strip()
            caste = request.form.get("caste").strip()

            city = request.form.get("city").strip()
            taluka = request.form.get("taluka").strip()
            district = request.form.get("district").strip()
            state = request.form.get("state").strip()

            admission_date = parse_date(request.form.get("admission_date"))
            student_class = request.form.get("class").strip()
            section = request.form.get("section").strip()
            previous_school = request.form.get("previous_school").strip()

            last_exam = request.form.get("last_exam").strip()
            result_status = request.form.get("result_status").strip()
            progress = request.form.get("progress").strip()
            conduct = request.form.get("conduct").strip()

            primary_mobile = request.form.get("primary_mobile").strip()
            alternate_mobile = request.form.get("alternate_mobile").strip()
            email = request.form.get("email" or "").strip().lower()
            occupation = request.form.get("occupation").strip()
            income = request.form.get("income").strip()
            guardian_name = request.form.get("guardian_name").strip()
            guardian_mobile = request.form.get("guardian_mobile").strip()

            # CHECK VALIDATION 
            if not is_valid_phone(primary_mobile):
                return "Invalid primary mobile number ❌"

            if alternate_mobile and not is_valid_phone(alternate_mobile):
                return "Invalid alternate mobile number ❌"

            if not is_valid_aadhaar(aadhaar):
                return "Invalid Aadhaar number ❌"
            

            # ================= DUPLICATE CHECK =================
            cursor.execute("""
                SELECT id
                FROM students
                WHERE
                    aadhaar = ?
                    OR student_uid = ?
                     
            """, (
                aadhaar,
                student_uid if student_uid else None
                 
            ))

            existing_student = cursor.fetchone()

            if existing_student:
                return "Student with same Aadhaar, Student UID already exists ❌"

                
            # GENERATE ONLY ON SAVE
            admission_no = generate_admission_no(school_id)   

            # ================= INSERT QUERY =================
            query = """
            INSERT INTO students (
               school_id,
                school_register_no, name, father_name, mother_name, student_uid, aadhaar, apaar_id,
                dob, birth_place, nationality, mother_tongue, religion, caste,
                city, taluka, district, state,
                admission_no, admission_date, class, section, previous_school,
                last_exam, result_status, progress, conduct,
                primary_mobile, alternate_mobile,email, occupation, income,
                guardian_name, guardian_mobile
            )
           VALUES (
            ?, ?,?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
        )
        """

            values = (
            school_id,
            school_register_no,
            name,
            father_name,
            mother_name,
            student_uid if student_uid else None,
            aadhaar,
            apaar_id if apaar_id else None,
            dob,
            birth_place,
            nationality,
            mother_tongue,
            religion,
            caste,
            city,
            taluka,
            district,
            state,
            admission_no,
            admission_date,
            student_class,
            section,
            previous_school,
            last_exam,
            result_status,
            progress,
            conduct,
            primary_mobile,
            alternate_mobile,
            email,
            occupation,
            income,
            guardian_name,
            guardian_mobile
        )

            cursor.execute(query, values)
            conn.commit()

            print("✅ Student Saved in DB")

           
            return redirect(url_for("clerk_students"))

        except Exception as e:

            if conn:
                conn.rollback()

            print("❌ ERROR:", e)
            return f"ERROR: {e}"

        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    school = get_school_details(session.get("clerk_school_id"))               

    return render_template(
        "clerk/add_student.html",
        next_admission=next_admission,
        role="clerk",
        school_name=school["school_name"],
        school_udise=school["school_udise"],
        active_page="add_student"
    )

# =========================================================
# ✏️ EDIT STUDENT (DB VERSION - FINAL SAFE)
# =========================================================
@app.route("/clerk/edit-student/<int:id>", methods=["GET", "POST"])
@login_required
def edit_student(id):

    conn = None
    cursor = None

    try:
        conn = get_connection()
        cursor = conn.cursor()

        school_id = session.get("clerk_school_id")

        if not school_id:
            return "School session missing ❌"

        # ================= FETCH STUDENT =================
        cursor.execute("""
            SELECT *
            FROM students
            WHERE id = ? AND school_id = ?
        """, (id, school_id))

        row = cursor.fetchone()

        if not row:
            return "Student Not Found ❌"

        # Convert to dict
        columns = [column[0] for column in cursor.description]
        student = dict(zip(columns, row))

        # ================= UPDATE =================
        if request.method == "POST":

            def get_val(field):
                val = request.form.get(field)
                return val if val not in [None, ""] else student.get(field)

            def get_date(field):
                val = request.form.get(field)
                return parse_date(val) if val else student.get(field)

            # ================= GET DATA =================
            school_register_no = get_val("school_register_no")
            name = get_val("name")
            father_name = get_val("father_name")
            mother_name = get_val("mother_name")
            student_uid = get_val("student_uid")
            aadhaar = get_val("aadhaar")
            apaar_id = get_val("apaar_id")

            dob = get_date("dob")
            birth_place = get_val("birth_place")
            nationality = get_val("nationality")
            mother_tongue = get_val("mother_tongue")
            religion = get_val("religion")
            caste = get_val("caste")

            city = get_val("city")
            taluka = get_val("taluka")
            district = get_val("district")
            state = get_val("state")

            admission_date = get_date("admission_date")
            student_class = get_val("class")
            section = get_val("section")
            previous_school = get_val("previous_school")

            last_exam = get_val("last_exam")
            result_status = get_val("result_status")
            progress = get_val("progress")
            conduct = get_val("conduct")

            primary_mobile = get_val("primary_mobile")
            alternate_mobile = get_val("alternate_mobile")
            email = get_val("email")
            occupation = get_val("occupation")
            income = get_val("income")
            guardian_name = get_val("guardian_name")
            guardian_mobile = get_val("guardian_mobile")

            # CHECK VALIDATION

            if not is_valid_phone(primary_mobile):
                return "Invalid primary mobile number ❌"

            if alternate_mobile and not is_valid_phone(alternate_mobile):
                return "Invalid alternate mobile number ❌"

            if not is_valid_aadhaar(aadhaar):
                return "Invalid Aadhaar number ❌"

            # ================= DUPLICATE CHECK =================
            cursor.execute("""
                SELECT id
                FROM students
                WHERE (
                    aadhaar = ?
                    OR (student_uid = ? AND ? != '')
                )
                AND id != ?
            """, (
                aadhaar,
                student_uid,
                student_uid,
                id
            ))

            existing_student = cursor.fetchone()

            if existing_student:
                return f"Student with same Aadhaar or Student UID already exists ❌"

            # ================= UPDATE QUERY =================
            cursor.execute("""
                UPDATE students SET
                    school_register_no=?,
                    name=?,
                    father_name=?,
                    mother_name=?,
                    student_uid=?,
                    aadhaar=?,
                    apaar_id=?,
                    dob=?,
                    birth_place=?,
                    nationality=?,
                    mother_tongue=?,
                    religion=?,
                    caste=?,
                    city=?,
                    taluka=?,
                    district=?,
                    state=?,
                    admission_date=?,
                    class=?,
                    section=?,
                    previous_school=?,
                    last_exam=?,
                    result_status=?,
                    progress=?,
                    conduct=?,
                    primary_mobile=?,
                    alternate_mobile=?,
                    email=?,
                    occupation=?,
                    income=?,
                    guardian_name=?,
                    guardian_mobile=?
                WHERE id=?
            """, (
                school_register_no,
                name,
                father_name,
                mother_name,
                student_uid,
                aadhaar,
                apaar_id,
                dob,
                birth_place,
                nationality,
                mother_tongue,
                religion,
                caste,
                city,
                taluka,
                district,
                state,
                admission_date,
                student_class,
                section,
                previous_school,
                last_exam,
                result_status,
                progress,
                conduct,
                primary_mobile,
                alternate_mobile,
                email,
                occupation,
                income,
                guardian_name,
                guardian_mobile,
                id
            ))

            conn.commit()

            print("✅ Student Updated in DB")

            return redirect(url_for("clerk_students"))

        school = get_school_details(school_id)

        return render_template(
            "clerk/edit_student.html",
            student=student,
            role="clerk",
            school_name=school["school_name"],
            school_udise=school["school_udise"],
            active_page="students"
        )

    except Exception as e:
        if conn:
            conn.rollback()

        print("❌ ERROR:", e)
        return f"Student update failed ❌ {e}"

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# =========================================================
# 📋 VIEW STUDENTS LIST PAGE
# =========================================================
@app.route("/clerk/students")
@login_required
def clerk_students():

    conn = None
    cursor = None

    try:
        conn = get_connection()
        cursor = conn.cursor()

        # ================= CLERK SESSION =================
        school_id = session.get("clerk_school_id")

        if not school_id:
            return "School session missing ❌"

        # ================= FETCH STUDENTS =================
        cursor.execute("""
            SELECT *
            FROM students
            WHERE school_id = ?
            ORDER BY id DESC
        """, (school_id,))

        rows = cursor.fetchall()

        # convert to dict
        columns = [column[0] for column in cursor.description]
        students = [dict(zip(columns, row)) for row in rows]

        # ================= SCHOOL DETAILS =================
        school = get_school_details(school_id)

        if not school:
            return "School not found ❌"

        return render_template(
            "clerk/students.html",
            students=students,
            role="clerk",
            school_name=school["school_name"],
            active_page="students"
        )

    except Exception as e:
        print("❌ STUDENTS FETCH ERROR:", e)
        return f"Students fetch failed ❌ {e}"

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


# =========================================================
# 📄 AUTO GENERATE TC NUMBER (ATOMIC + SAFE)
# =========================================================
def generate_tc_number(school_id):

    conn = None
    cursor = None

    try:
        school_code = get_school_code(school_id)

        conn = get_connection()
        cursor = conn.cursor()

        # ================= ATOMIC UPDATE =================
        cursor.execute("""
            UPDATE school_sequences
            SET tc_last_number = tc_last_number + 1
            OUTPUT inserted.tc_last_number
            WHERE school_id = ?
        """, (school_id,))

        row = cursor.fetchone()

        if not row:
            raise Exception("School sequence not found ❌")

        next_number = row[0]

        conn.commit()

        return f"{school_code}-TC-{str(next_number).zfill(4)}"

    except Exception as e:
        if conn:
            conn.rollback()
        print("❌ TC NUMBER ERROR:", e)
        raise

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


# =========================================================
# 📄 TC FORM (DB VERSION - SAFE + ATOMIC)
# =========================================================
@app.route("/clerk/tc-form/<int:id>", methods=["GET", "POST"])
@login_required
def tc_form(id):

    print("==== TC FORM HIT ====")
    print("Method:", request.method)
    print("TC route hit")

    # CLERK ONLY
    if not session.get("clerk_logged_in"):
        return redirect(url_for("login"))

    if session.get("clerk_role") != "clerk":
        return "Unauthorized ❌"

    conn = None
    cursor = None

    try:
        conn = get_connection()
        cursor = conn.cursor()

        print("clerk_logged_in:", session.get("clerk_logged_in"))
        print("clerk_role:", session.get("clerk_role"))
        print("school_id:", session.get("clerk_school_id"))

        school_id = session.get("clerk_school_id")

        if not school_id:
            return redirect(url_for("login"))

        # GET STUDENT
        cursor.execute("""
            SELECT *
            FROM students
            WHERE id = ? AND school_id = ?
        """, (id, school_id))

        row = cursor.fetchone()

        if not row:
            return "Student Not Found ❌"

        columns = [column[0] for column in cursor.description]
        student = dict(zip(columns, row))

        if request.method == "POST":

            tc_date_raw = request.form.get("tc_date", "").strip()
            leaving_date_raw = request.form.get("leaving_date", "").strip()
            leaving_reason = request.form.get("leaving_reason", "").strip()
            remark = request.form.get("remark", "").strip()

            tc_date = parse_date(tc_date_raw)
            leaving_date = parse_date(leaving_date_raw)

            if not leaving_reason:
                return "Leaving reason required ❌"

            if not tc_date or not leaving_date:
                return "TC Date / Leaving Date invalid ❌"

            admission_date = student.get("admission_date")

            if admission_date:

                # normalize both to date only
                if hasattr(admission_date, "date"):
                    admission_date = admission_date.date()

                if hasattr(leaving_date, "date"):
                    leaving_date_only = leaving_date.date()
                else:
                    leaving_date_only = leaving_date

                if leaving_date_only < admission_date:
                    return "Leaving date cannot be before admission date ❌"
                

            # EXISTING TC CHECK
            cursor.execute("""
                SELECT id
                FROM tc
                WHERE student_id = ? AND school_id = ?
            """, (id, school_id))

            existing_tc = cursor.fetchone()

            if existing_tc:
                return redirect(
                    url_for("view_tc", tc_id=existing_tc[0])
                )

            # GENERATE TC NUMBER
            tc_number = generate_tc_number(school_id)

            print("TC insert starting")
            print("Student ID:", id)
            print("School ID:", school_id)

            # INSERT
            cursor.execute("""
                INSERT INTO tc (
                    school_id,
                    student_id,
                    tc_number,
                    tc_date,
                    leaving_date,
                    leaving_reason,
                    remark
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                school_id,
                id,
                tc_number,
                tc_date,
                leaving_date,
                leaving_reason,
                remark
            ))

            conn.commit()

            cursor.execute("""
                SELECT TOP 1 id
                FROM tc
                WHERE student_id = ?
                AND school_id = ?
                ORDER BY id DESC
            """, (id, school_id))

            new_tc = cursor.fetchone()

            if new_tc:
                return redirect(
                    url_for("view_tc", tc_id=new_tc[0])
                )

            return redirect(url_for("tc_search"))

        school = get_school_details(school_id)

        if not school:
            return "School not found ❌"

        return render_template(
            "clerk/tc_form.html",
            student=student,
            tc_number="Auto Generate On Save",
            role="clerk",
            school_name=school["school_name"],
            school_udise=school["school_udise"],
            active_page="students"
        )

    except Exception as e:
        if conn:
            conn.rollback()

        print("❌ TC FORM ERROR:", e)
        return "TC form failed ❌"

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

 
# =========================================================
# 👁️ VIEW TC (MAIN DISPLAY PAGE)
# =========================================================
@app.route("/clerk/tc/view/<int:tc_id>")
@login_required
def view_tc(tc_id):

    mode = request.args.get("mode", "").strip()

    conn = None
    cursor = None

    try:
        conn = get_connection()
        cursor = conn.cursor()

        # ============================================
        # ADMIN MODE → no school restriction
        # ============================================
        if (
            mode == "admin"
            and session.get("admin_logged_in")
            and session.get("admin_role") == "admin"
        ):

            cursor.execute("""
                SELECT 
                    t.*,
                    s.name,
                    s.school_register_no,
                    s.student_uid,
                    s.apaar_id,
                    s.class AS class_name,
                    s.admission_no,
                    s.father_name,
                    s.mother_name,
                    s.nationality,
                    s.mother_tongue,
                    s.religion,
                           
                    s.caste,
                    s.birth_place,
                    s.city,
                    s.taluka,
                    s.district,
                    s.state,
                    s.dob,
                    s.previous_school,
                    s.admission_date,
                    s.progress,
                    s.conduct,
                    s.aadhaar,
                    s.primary_mobile,
                    s.email,
                           
                           
                    sc.name as school_name,
                    sc.address,
                    sc.phone,
                    sc.email,
                    sc.udise_no,
                    sc.recognition_no,
                    sc.medium,
                    sc.school_index_no,
                    sc.board_name,
                    sc.logo_path,
                    sc.watermark_path,
                    sc.website
                FROM tc t
                JOIN students s
                    ON t.student_id = s.id
                JOIN schools sc
                    ON t.school_id = sc.school_id
                WHERE t.id = ?
            """, (tc_id,))

            role = "admin"

        # ============================================
        # CLERK MODE → own school only
        # ============================================
        else:

            school_id = session.get("clerk_school_id")

            if not school_id:
                return "School session missing ❌"

            cursor.execute("""
                SELECT 
                    t.*,
                    s.name,
                    s.school_register_no,
                    s.student_uid,
                    s.apaar_id,
                    s.class AS class_name,
                    s.admission_no,
                    s.father_name,
                    s.mother_name,
                    s.nationality,
                    s.mother_tongue,
                    s.religion,
                           
                    s.caste,
                    s.birth_place,
                    s.city,
                    s.taluka,
                    s.district,
                    s.state,
                    s.dob,
                    s.previous_school,
                    s.admission_date,
                    s.progress,
                    s.conduct,
                    s.aadhaar,
                    s.primary_mobile,
                    s.email,
                           
                    sc.name as school_name,
                    sc.address,
                    sc.phone,
                    sc.email,
                    sc.udise_no,
                    sc.recognition_no,
                    sc.medium,
                    sc.school_index_no,
                    sc.board_name,
                    sc.logo_path,
                    sc.watermark_path,
                    sc.website
                FROM tc t
                JOIN students s
                    ON t.student_id = s.id
                JOIN schools sc
                    ON t.school_id = sc.school_id
                WHERE t.id = ? AND t.school_id = ?
            """, (
                tc_id,
                school_id
            ))

            role = "clerk"

        row = cursor.fetchone()

        if not row:
            return "TC Not Found ❌"

        tc = {
            "id": row.id,
            "tc_number": row.tc_number,
            "tc_date": format_date(row.tc_date),
            "leaving_date": format_date(row.leaving_date),
            "leaving_reason": row.leaving_reason,
            "remark": row.remark
        }

        student = {
            "id": row.student_id,
            "school_register_no": row.school_register_no or "",
            "student_uid": row.student_uid or "",
            "apaar_id": row.apaar_id or "",
            "name": row.name,
            "class_name": row.class_name,
            "admission_no": row.admission_no,
            "father_name": row.father_name or "",
            "mother_name": row.mother_name or "",
            "nationality": row.nationality or "",
            "mother_tongue": row.mother_tongue or "",
            "religion": row.religion or "",
            "caste": row.caste or "",
            "birth_place": row.birth_place or "",
            "city": row.city or "",
            "taluka": row.taluka or "",
            "district": row.district or "",
            "state": row.state or "",
            "dob": format_date(row.dob),
            "previous_school": row.previous_school or "",
            "admission_date": format_date(row.admission_date),
            "progress": row.progress or "",
            "conduct": row.conduct or "",
            "aadhaar": row.aadhaar or "",
            "primary_mobile": row.primary_mobile or "",
            "email": row.email or "",

        }

        school = {
            "name": row.school_name,
            "address": row.address or "",
            "phone": row.phone or "",
            "email": row.email or "",
            "udise_no": row.udise_no or "",
            "recognition_no": row.recognition_no or "",
            "medium": row.medium or "",
            "school_index_no": row.school_index_no or "",
            "board_name": row.board_name or "",
            "logo_path": row.logo_path or "",
            "watermark_path": row.watermark_path or "",
            "website": row.website or ""
        }

        return render_template(
            "clerk/tc_generate.html",
            student=student,
            tc=tc,
            school=school,
            role=role,
            school_name=school["name"],
            school_address=school["address"],
            school_phone=school["phone"],
            school_email=school["email"],
            school_udise=school["udise_no"],
            school_recognition_no=school["recognition_no"],
            school_medium=school["medium"],
            school_index_no=school["school_index_no"],
            school_board_name=school["board_name"],
            school_logo=school["logo_path"],
            school_watermark=school["watermark_path"],
            school_website=school["website"]
        )

    except Exception as e:
        print("❌ VIEW TC ERROR:", e)
        return "TC view failed ❌"

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

            
# =========================================================
# 📄 DOWNLOAD TC PDF (HTML → PDFKIT)
# =========================================================

import pdfkit
import os
from flask import render_template, send_file, request, session


@app.route("/clerk/tc/pdf/<int:tc_id>")
@login_required
def download_tc_pdf(tc_id):

    conn = None
    cursor = None

    try:
        mode = request.args.get("mode")
        school_id = session.get("clerk_school_id")

        if not school_id:
                return "School session missing ❌"

        conn = get_connection()
        cursor = conn.cursor()

        # =====================================================
        # ADMIN MODE
        # =====================================================
        if (
            mode == "admin"
            and session.get("admin_logged_in")
            and session.get("admin_role") == "admin"
        ):

            cursor.execute("""
            SELECT 
                t.*,

                s.school_register_no,
                s.student_uid,
                s.apaar_id,
                s.name,
                s.father_name,
                s.mother_name,
                s.class AS class_name,
                s.admission_no,
                s.dob,
                s.aadhaar,
                s.primary_mobile,
                s.email,

                s.birth_place,
                s.nationality,
                s.mother_tongue,
                s.religion,
                s.caste,

                s.city,
                s.taluka,
                s.district,
                s.state,

                s.admission_date,
                s.section,
                s.previous_school,
                s.last_exam,
                s.result_status,

                s.progress,
                s.conduct,

                sc.name AS school_name,
                sc.address,
                sc.phone,
                sc.email,
                sc.udise_no,
                sc.recognition_no,
                sc.medium,
                sc.school_index_no,
                sc.board_name,
                sc.logo_path,
                sc.watermark_path,
                sc.website

            FROM tc t
            JOIN students s ON t.student_id = s.id
            JOIN schools sc ON t.school_id = sc.school_id
            WHERE t.id = ?
            """, (tc_id,))

        # =====================================================
        # CLERK MODE
        # =====================================================
        else:

            cursor.execute("""
            SELECT 
                t.*,

                s.school_register_no,
                s.student_uid,
                s.apaar_id,
                s.name,
                s.father_name,
                s.mother_name,
                s.class AS class_name,
                s.admission_no,
                s.dob,
                s.aadhaar,
                s.primary_mobile,
                s.email,
                s.birth_place,
                s.nationality,
                s.mother_tongue,
                s.religion,
                s.caste,

                s.city,
                s.taluka,
                s.district,
                s.state,

                s.admission_date,
                s.section,
                s.previous_school,
                s.last_exam,
                s.result_status,

                s.progress,
                s.conduct,

                sc.name AS school_name,
                sc.address,
                sc.phone,
                sc.email,
                sc.udise_no,
                sc.recognition_no,
                sc.medium,
                sc.school_index_no,
                sc.board_name,
                sc.logo_path,
                sc.watermark_path,
                sc.website

            FROM tc t
            JOIN students s ON t.student_id = s.id
            JOIN schools sc ON t.school_id = sc.school_id
            WHERE t.id = ? AND t.school_id = ?
            """, (tc_id, school_id))

        row = cursor.fetchone()

        if not row:
            return "TC Not Found ❌"

        # =====================================================
        # TC DATA
        # =====================================================
        tc = {
            "id": row.id,
            "tc_number": row.tc_number,
            "tc_date": format_date(row.tc_date),
            "leaving_date": format_date(row.leaving_date),
            "leaving_reason": row.leaving_reason,
            "remark": row.remark
        }

        # =====================================================
        # STUDENT DATA
        # =====================================================
        student = {
            "school_register_no": row.school_register_no,
            "student_uid": row.student_uid,
            "apaar_id": row.apaar_id,
            "name": row.name,
            "father_name": row.father_name,
            "mother_name": row.mother_name,
            "class_name": row.class_name,
            "admission_no": row.admission_no,
            "dob": format_date(row.dob),
            "aadhaar": row.aadhaar,
            "primary_mobile": row.primary_mobile or "",
            "email": row.email or "",
            "birth_place": row.birth_place,
            "nationality": row.nationality,
            "mother_tongue": row.mother_tongue,
            "religion": row.religion,
            "caste": row.caste,
            "city": row.city,
            "taluka": row.taluka,
            "district": row.district,
            "state": row.state,
            "admission_date": format_date(row.admission_date),
            "section": row.section,
            "previous_school": row.previous_school,
            "last_exam": row.last_exam,
            "result_status": row.result_status,
            "progress": row.progress,
            "conduct": row.conduct
        }

        # =====================================================
        # SCHOOL DATA
        # =====================================================

        base_dir = os.path.abspath(os.path.dirname(__file__))

        logo_absolute = ""
        watermark_absolute = ""

        if row.logo_path:
            logo_absolute = "file:///" + os.path.join(
                base_dir,
                "static",
                row.logo_path.replace("static/", "")
            ).replace("\\", "/")

        if row.watermark_path:
            watermark_absolute = "file:///" + os.path.join(
                base_dir,
                "static",
                row.watermark_path.replace("static/", "")
            ).replace("\\", "/")

        school = {
            "name": row.school_name,
            "address": row.address or "",
            "phone": row.phone or "",
            "email": row.email or "",
            "udise_no": row.udise_no or "",
            "recognition_no": row.recognition_no or "",
            "medium": row.medium or "",
            "school_index_no": row.school_index_no or "",
            "board_name": row.board_name or "",
            "logo_path": logo_absolute,
            "watermark_path": watermark_absolute,
            "website": row.website or ""
        }

        # =====================================================
        # RENDER HTML
        # =====================================================
        html = render_template(
            "clerk/tc_generate.html",
            tc=tc,
            student=student,
            school=school,
            is_pdf=True
        )

        # =====================================================
        # PDF SAVE FOLDER
        # =====================================================
        pdf_folder = os.path.join("static", "generated_tc")

        if not os.path.exists(pdf_folder):
            os.makedirs(pdf_folder)

        pdf_path = os.path.join(
            pdf_folder,
            f"tc_{tc['id']}.pdf"
        )

        # =====================================================
        # PDF OPTIONS
        # =====================================================
        options = {
            "page-size": "A4",
            "margin-top": "5mm",
            "margin-right": "5mm",
            "margin-bottom": "5mm",
            "margin-left": "5mm",
            "encoding": "UTF-8",
            "enable-local-file-access": ""
        }

        # =====================================================
        # GENERATE PDF
        # =====================================================

        pdfkit.from_string(

            html,
            pdf_path,
            configuration=pdf_config,
             options=options
        )

        # =====================================================
        # 📧 AUTO SEND TC PDF EMAIL
        # =====================================================

        try:

            student_email = student.get("email")

            if student_email:

                # =========================================
                # CHECK ALREADY SENT
                # =========================================

                cursor.execute("""

                    SELECT id
                    FROM tc_email_logs
                    WHERE school_id = ?
                    AND tc_id = ?

                """, (

                    school_id,
                    tc["id"]

                ))

                already_sent = cursor.fetchone()

                # =========================================
                # SEND ONLY ONCE
                # =========================================

                if not already_sent:

                    subject = (
                        f"Transfer Certificate - {student['name']}"
                    )

                    body = f"""

                    <div style="font-family:Arial;padding:20px;">

                        <h2 style="color:#14b8a6;">
                            Transfer Certificate Generated
                        </h2>

                        <p>
                            Dear Parent/Student,
                        </p>

                        <p>
                            Your Transfer Certificate has been generated successfully.
                        </p>

                        <hr>

                        <p>
                            <b>Student Name:</b>
                            {student['name']}
                        </p>

                        <p>
                            <b>TC Number:</b>
                            {tc['tc_number']}
                        </p>

                        <p>
                            <b>School:</b>
                            {school['name']}
                        </p>

                        <hr>

                        <p>
                            Please find the TC PDF attached.
                        </p>

                        <p>
                            Thank you,
                            <br>
                            <b>{school['name']}</b>
                        </p>

                    </div>

                    """

                    # =========================================
                    # SEND MAIL WITH ATTACHMENT
                    # =========================================

                    email_sent = send_email(

                        student_email,
                        subject,
                        body,
                        pdf_path,
                        f"{tc['tc_number']}.pdf"

                    )

                    # =========================================
                    # EMAIL SUCCESS
                    # =========================================

                    if email_sent == True:

                        print("✅ TC PDF EMAIL SENT")

                        # =====================================
                        # SAVE EMAIL LOG
                        # =====================================

                        cursor.execute("""

                            INSERT INTO tc_email_logs
                            (
                                school_id,
                                tc_id,
                                student_email
                            )
                            VALUES (?, ?, ?)

                        """, (

                            school_id,
                            tc["id"],
                            student_email

                        ))

                        conn.commit()

                    # =========================================
                    # EMAIL FAILED
                    # =========================================

                    else:

                        print(
                            "❌ TC EMAIL FAILED:",
                            email_sent
                        )

        except Exception as email_error:

            print(
                "❌ TC EMAIL ERROR:",
                email_error
            )

        # =====================================================
        # RETURN FILE
        # =====================================================
        return send_file(
            pdf_path,
            as_attachment=True,
            download_name=f"{tc['tc_number']}.pdf"
        )

    except Exception as e:
        print("❌ TC PDF ERROR:", e)
        return f"ERROR: {e}"

    finally:
        if cursor:
            cursor.close()

        if conn:
            conn.close()

# =========================================================
# 🔓 PUBLIC TC VIEW (SAFE PUBLIC VERIFY) FOR PARENT WP
# =========================================================
@app.route("/public/tc/<int:tc_id>")
def public_tc(tc_id):

    conn = None
    cursor = None

    try:
        conn = get_connection()
        cursor = conn.cursor()

        # ================= GET FULL TC DATA =================
        cursor.execute("""
            SELECT
                t.*,

                s.name,
                s.father_name,
                s.mother_name,
                s.class AS class_name,
                s.admission_no,
                s.dob,
                s.aadhaar,
                s.birth_place,
                s.nationality,
                s.mother_tongue,
                s.religion,
                s.caste,
                s.city,
                s.taluka,
                s.district,
                s.state,
                s.admission_date,
                s.section,
                s.previous_school,
                s.last_exam,
                s.result_status,
                s.progress,
                s.conduct,

                sc.name AS school_name,
                sc.address,
                sc.phone,
                sc.email,
                sc.udise_no,
                sc.recognition_no,
                sc.medium,
                sc.school_index_no,
                sc.board_name,
                sc.logo_path,
                sc.watermark_path,
                sc.website

            FROM tc t
            JOIN students s
                ON t.student_id = s.id
            JOIN schools sc
                ON t.school_id = sc.school_id
            WHERE t.id = ?
        """, (tc_id,))

        row = cursor.fetchone()

        if not row:
            return "TC Not Found ❌"

        # ================= TC =================
        tc = {
            "id": row.id,
            "tc_number": row.tc_number,
            "tc_date": format_date(row.tc_date),
            "leaving_date": format_date(row.leaving_date),
            "leaving_reason": row.leaving_reason,
            "remark": row.remark
        }

        # ================= STUDENT =================
        student = {
            "name": row.name,
            "father_name": row.father_name,
            "mother_name": row.mother_name,
            "class_name": row.class_name,
            "admission_no": row.admission_no,
            "dob": format_date(row.dob),
            "aadhaar": "XXXX-XXXX-" + str(row.aadhaar)[-4:] if row.aadhaar else "",
            "birth_place": row.birth_place,
            "nationality": row.nationality,
            "mother_tongue": row.mother_tongue,
            "religion": row.religion,
            "caste": row.caste,
            "city": row.city,
            "taluka": row.taluka,
            "district": row.district,
            "state": row.state,
            "admission_date": format_date(row.admission_date),
            "section": row.section,
            "previous_school": row.previous_school,
            "last_exam": row.last_exam,
            "result_status": row.result_status,
            "progress": row.progress,
            "conduct": row.conduct
        }

        # ================= SCHOOL =================
        school = {
            "name": row.school_name,
            "address": row.address or "",
            "phone": row.phone or "",
            "email": row.email or "",
            "udise_no": row.udise_no or "",
            "recognition_no": row.recognition_no or "",
            "medium": row.medium or "",
            "school_index_no": row.school_index_no or "",
            "board_name": row.board_name or "",
            "logo_path": row.logo_path or "",
            "watermark_path": row.watermark_path or "",
            "website": row.website or ""
        }

        return render_template(
            "clerk/tc_generate.html",
            tc=tc,
            student=student,
            school=school,
            school_name=school["name"],
            school_address=school["address"],
            school_phone=school["phone"],
            school_email=school["email"],
            school_udise=school["udise_no"],
            school_recognition_no=school["recognition_no"],
            school_medium=school["medium"],
            school_index_no=school["school_index_no"],
            school_board_name=school["board_name"],
            school_logo_path=school["logo_path"],
            school_watermark_path=school["watermark_path"],
            school_website=school["website"],
            is_public=True
        )

    except Exception as e:
        print("❌ PUBLIC TC ERROR:", e)
        return f"ERROR: {e}"

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# =========================================================
# 📊 TC HISTORY PAGE (SAFE + CORRECT ANALYTICS)
# =========================================================
@app.route("/clerk/tc")
@login_required
def clerk_tc_page():

    conn = None
    cursor = None

    try:
        school_id = session.get("clerk_school_id")

        if not school_id:
            return "School session missing ❌"

        conn = get_connection()
        cursor = conn.cursor()

        # ================= MAIN TC LIST =================
        cursor.execute("""
        SELECT 
            t.id,
            t.tc_number,
            t.tc_date,
            s.name,
            s.class AS class_name,
            s.admission_no
        FROM tc t
        JOIN students s 
            ON t.student_id = s.id
            AND s.school_id = t.school_id
        WHERE t.school_id = ?
        ORDER BY t.id DESC
        """, (school_id,))

        rows = cursor.fetchall()

        tc_list = []

        for r in rows:
            tc_list.append({
                "id": r.id,
                "tc_number": r.tc_number,
                "tc_date": format_date(r.tc_date),
                "name": r.name,
                "class": r.class_name,
                "admission_no": r.admission_no
            })

        # ================= TOTAL COUNT =================
        cursor.execute("""
            SELECT COUNT(*)
            FROM tc
            WHERE school_id = ?
        """, (school_id,))

        total_tc = cursor.fetchone()[0]

        # ================= TODAY COUNT =================
        cursor.execute("""
            SELECT COUNT(*)
            FROM tc
            WHERE school_id = ?
            AND CAST(created_at AS DATE) = CAST(GETDATE() AS DATE)
        """, (school_id,))

        today_tc = cursor.fetchone()[0]

        # ================= MONTH COUNT =================
        cursor.execute("""
            SELECT COUNT(*)
            FROM tc
            WHERE school_id = ?
            AND MONTH(created_at) = MONTH(GETDATE())
            AND YEAR(created_at) = YEAR(GETDATE())
        """, (school_id,))

        month_tc = cursor.fetchone()[0]


        school = get_school_details(school_id)

        if not school:
            return "School not found ❌"

        return render_template(
            "clerk/tc_search.html",
            role="clerk",
            school_name= school["school_name"],
            school_udise=school["school_udise"],
            active_page="tc",
            tc_list=tc_list,
            recent_tc=tc_list[:5],
            total_tc=total_tc,
            today_tc=today_tc,
            month_tc=month_tc
        )

    except Exception as e:
        print("❌ TC PAGE ERROR:", e)
        return f"ERROR: {e}"

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


# =========================================================
# 🧾 AUTO GENERATE BONAFIDE NUMBER (ATOMIC + SAFE)
# =========================================================
def generate_bonafide_number(school_id):

    conn = None
    cursor = None

    try:
        school_code = get_school_code(school_id)

        conn = get_connection()
        cursor = conn.cursor()

        # ================= ATOMIC UPDATE =================
        cursor.execute("""
            UPDATE school_sequences
            SET bonafide_last_number = bonafide_last_number + 1
            OUTPUT inserted.bonafide_last_number
            WHERE school_id = ?
        """, (school_id,))

        row = cursor.fetchone()

        if not row:
            raise Exception("School sequence not found ❌")

        next_number = row[0]

        conn.commit()

        return f"{school_code}-BON-{str(next_number).zfill(4)}"

    except Exception as e:
        if conn:
            conn.rollback()

        print("❌ BONAFIDE NUMBER ERROR:", e)
        raise

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


# =========================================================
# 📜 BONAFIDE PAGE
# =========================================================
@app.route("/clerk/bonafide/")
@login_required
def clerk_bonafide_page():

    conn = None
    cursor = None

    try:

        school_id = session.get("clerk_school_id")

        if not school_id:
            return "School session missing ❌"

        conn = get_connection()
        cursor = conn.cursor()

        # ================= SCHOOL INFO =================
        cursor.execute("""
            SELECT
                school_id,
                name,
                school_code
            FROM schools
            WHERE school_id = ?
        """, (school_id,))

        school = cursor.fetchone()

        if not school:
            return "School not found ❌"

        school_name = school.name
        school_code = school.school_code

        # ================= STUDENTS =================
        cursor.execute("""
            SELECT
                id,
                school_register_no,
                name,
                admission_no,
                student_uid,
                apaar_id,
                class AS class_name,
                primary_mobile,
                email
            FROM students
            WHERE school_id = ?
            ORDER BY id DESC
        """, (school_id,))

        student_rows = cursor.fetchall()

        students = []

        for r in student_rows:

            students.append({

                "id": r.id,
                "school_register_no": r.school_register_no,
                "name": r.name,
                "admission_no": r.admission_no,
                "student_uid": r.student_uid,
                "apaar_id": r.apaar_id,
                "primary_mobile": r.primary_mobile or "",
                "email": r.email or "",
                "class": r.class_name

            })

        # ================= BONAFIDE LIST =================
        cursor.execute("""
            SELECT

                b.id,
                b.student_id,
                b.bonafide_number,
                b.date,
                b.purpose,

                s.school_register_no,
                s.name,
                s.admission_no,
                s.student_uid,
                s.apaar_id,
                s.primary_mobile,
                s.email,

                s.class AS class_name

            FROM bonafide b

            JOIN students s
                ON b.student_id = s.id
                AND s.school_id = b.school_id

            WHERE b.school_id = ?

            ORDER BY b.id DESC

        """, (school_id,))

        rows = cursor.fetchall()

        bonafide_list = []

        for r in rows:

            bonafide_list.append({

                "id": r.id,
                "student_id": r.student_id,
                "bonafide_number": r.bonafide_number,
                "date": format_date(r.date),
                "purpose": r.purpose,

                "school_register_no": r.school_register_no,
                "name": r.name,
                "admission_no": r.admission_no,
                "student_uid": r.student_uid,
                "apaar_id": r.apaar_id,

                "primary_mobile": r.primary_mobile or "",
                "email": r.email or "",

                "class": r.class_name

            })

        # ================= TOTAL =================
        cursor.execute("""
            SELECT COUNT(*)
            FROM bonafide
            WHERE school_id = ?
        """, (school_id,))

        total_bonafide = cursor.fetchone()[0]

        # ================= TODAY =================
        cursor.execute("""
            SELECT COUNT(*)
            FROM bonafide
            WHERE school_id = ?
            AND CAST(created_at AS DATE) = CAST(GETDATE() AS DATE)
        """, (school_id,))

        today_bonafide = cursor.fetchone()[0]

        # ================= MONTH =================
        cursor.execute("""
            SELECT COUNT(*)
            FROM bonafide
            WHERE school_id = ?
            AND MONTH(created_at) = MONTH(GETDATE())
            AND YEAR(created_at) = YEAR(GETDATE())
        """, (school_id,))

        month_bonafide = cursor.fetchone()[0]

        # ================= RENDER =================
        return render_template(

            "clerk/bonafide.html",

            role="clerk",

            school_name=school_name,
            school_code=school_code,

            active_page="bonafide",

            students=students,

            bonafide_list=bonafide_list,
            recent_bonafide=bonafide_list[:5],

            total_bonafide=total_bonafide,
            today_bonafide=today_bonafide,
            month_bonafide=month_bonafide,

            next_bonafide_number="Auto Generate On Save"

        )

    except Exception as e:

        print("❌ BONAFIDE PAGE ERROR:", e)
        return f"ERROR: {e}"

    finally:

        if cursor:
            cursor.close()

        if conn:
            conn.close()


# =========================================================
# 📄 SAVE BONAFIDE (DB VERSION - FULL FIXED)
# =========================================================
@app.route("/clerk/bonafide/save", methods=["POST"])
@login_required
def save_bonafide():

    conn = None
    cursor = None

    try:
        school_id = session.get("clerk_school_id")
        student_id = request.form.get("student_id")
        purpose = request.form.get("purpose", "").strip()
        date = parse_date(request.form.get("date"))

        if not purpose or not purpose.strip():
            return "Purpose required ❌"

        if not date:
            return "Invalid date ❌"


        if not school_id:
            return "School session missing ❌"

        if not student_id:
            return "Student ID missing ❌"

        try:
            student_id = int(student_id)
        except ValueError:
            return "Invalid Student ID ❌"

        conn = get_connection()
        cursor = conn.cursor()

        # ================= CHECK STUDENT =================
        cursor.execute("""
            SELECT id
            FROM students
            WHERE id = ? AND school_id = ?
        """, (student_id, school_id))

        student = cursor.fetchone()

        if not student:
            return "Student Not Found ❌"
        
        # ================= CHECK EXISTING BONAFIDE =================
        cursor.execute("""
        SELECT TOP 1 id
        FROM bonafide
        WHERE student_id = ?
        AND school_id = ?
        AND purpose = ?
    """, (student_id, school_id, purpose))

        existing_bonafide = cursor.fetchone()

        # IF EXISTS → OPEN EXISTING
        if existing_bonafide:
            return redirect(
                url_for(
                    "view_bonafide",
                    bid=existing_bonafide[0]
                )
            )

       # ================= GENERATE NUMBER =================
        bonafide_number = generate_bonafide_number(school_id)

        # ================= INSERT =================
        cursor.execute("""
            INSERT INTO bonafide (
                school_id,
                student_id,
                bonafide_number,
                purpose,
                date
            )
            OUTPUT inserted.id
            VALUES (?, ?, ?, ?, ?)
        """, (
            school_id,
            student_id,
            bonafide_number,
            purpose,
            date
        ))

        bonafide_id = cursor.fetchone()[0]

        conn.commit()

        print("✅ BONAFIDE SAVED")

        return redirect(
            url_for(
                "view_bonafide",
                bid=bonafide_id
            )
        )

    except Exception as e:

        if conn:
            conn.rollback()

        print("❌ BONAFIDE SAVE ERROR:", e)
        return f"ERROR: {e}"

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


# =========================================================
# 👁️ VIEW BONAFIDE (PRINT PAGE)
# =========================================================
@app.route("/clerk/bonafide/view/<int:bid>")
@login_required
def view_bonafide(bid):


    conn = None
    cursor = None

    try:
        conn = get_connection()
        cursor = conn.cursor()

        mode = request.args.get("mode")
        school_id = session.get("clerk_school_id")

         # ================= ADMIN MODE =================
        if mode == "admin" and session.get("admin_role") == "admin":

            cursor.execute("""
                SELECT 
                    b.*,
                    s.name,
                    s.class,
                    s.admission_date,
                    s.dob,
                    s.caste,
                    s.primary_mobile,
                    s.email,
                    s.school_register_no,
                     

                    sc.name AS school_name,
                    sc.address,
                    sc.phone,
                    sc.email AS school_email
                           

                FROM bonafide b
                JOIN students s ON b.student_id = s.id
                JOIN schools sc ON b.school_id = sc.school_id
                WHERE b.id = ?
            """, (bid,))

            # ================= CLERK MODE =================
        else:

            cursor.execute("""
                SELECT 
                    b.*,
                    s.name,
                    s.class,
                    s.admission_date,
                    s.dob,
                    s.caste,
                    s.primary_mobile,
                    s.email,
                    s.school_register_no,
                   

                    sc.name AS school_name,
                    sc.address,
                    sc.phone,
                    sc.email AS school_email

                FROM bonafide b
                JOIN students s ON b.student_id = s.id
                JOIN schools sc ON b.school_id = sc.school_id
                WHERE b.id = ? AND b.school_id = ?
            """, (bid, school_id))
    
        row = cursor.fetchone()

        if not row:
            return "Bonafide Not Found ❌"

        columns = [col[0] for col in cursor.description]
        data = dict(zip(columns, row))

            

            # ================= STUDENT DATA =================
        student = {
            "name": data.get("name") or "",
            "class": data.get("class") or "",
            "admission_date": format_date(data.get("admission_date")),
            "dob": format_date(data.get("dob")),
            "caste": data.get("caste") or "",
            "primary_mobile": data.get("primary_mobile") or "",
            "email": data.get("school_email") or "",
            "school_register_no": data.get("school_register_no") or "",
            
        }

        # ================= BONAFIDE DATA =================
        bonafide = {
            "id": data.get("id"),
            "bonafide_number": data.get("bonafide_number"),
            "purpose": data.get("purpose") or "",
            "date": format_date(data.get("date"))
        }

        # ================= SCHOOL DATA =================
        school = {
            "name": data.get("school_name") or "",
            "address": data.get("address") or "",
            "phone": data.get("phone") or "",
            "email": data.get("email") or ""
        }

        return render_template(
            "clerk/bonafide_generate.html",
            student=student,
            bonafide=bonafide,
            school=school
        )

    except Exception as e:
        print("❌ VIEW BONAFIDE ERROR:", e)
        return f"ERROR: {e}"

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# =========================================================
# 📄 DOWNLOAD BONAFIDE PDF
# =========================================================
@app.route("/clerk/bonafide/pdf/<int:bid>")
@login_required
def download_bonafide_pdf(bid):

    conn = None
    cursor = None

    try:

        mode = request.args.get("mode")

        school_id = session.get("clerk_school_id")

        conn = get_connection()
        cursor = conn.cursor()

        # =====================================================
        # ADMIN MODE
        # =====================================================
        if (
            mode == "admin"
            and session.get("admin_logged_in")
            and session.get("admin_role") == "admin"
        ):

            cursor.execute("""

                SELECT

                    b.*,

                    s.name,
                    s.school_register_no,
                    s.class,
                    s.admission_date,
                    s.dob,
                    s.caste,
                    s.primary_mobile,

                    s.email AS student_email,

                    sc.name AS school_name,
                    sc.address,
                    sc.phone,

                    sc.email AS school_email,

                    sc.logo_path,
                    sc.watermark_path,
                    sc.website

                FROM bonafide b

                JOIN students s
                    ON b.student_id = s.id

                JOIN schools sc
                    ON b.school_id = sc.school_id

                WHERE b.id = ?

            """, (bid,))

        # =====================================================
        # CLERK MODE
        # =====================================================
        else:

            if not school_id:
                return "School session missing ❌"

            cursor.execute("""

                SELECT

                    b.*,

                    s.name,
                    s.school_register_no,
                    s.class,
                    s.admission_date,
                    s.dob,
                    s.caste,
                    s.primary_mobile,

                    s.email AS student_email,

                    sc.name AS school_name,
                    sc.address,
                    sc.phone,

                    sc.email AS school_email,

                    sc.logo_path,
                    sc.watermark_path,
                    sc.website

                FROM bonafide b

                JOIN students s
                    ON b.student_id = s.id

                JOIN schools sc
                    ON b.school_id = sc.school_id

                WHERE b.id = ?
                AND b.school_id = ?

            """, (

                bid,
                school_id

            ))

        row = cursor.fetchone()

        if not row:
            return "Bonafide Not Found ❌"

        # =====================================================
        # BONAFIDE DATA
        # =====================================================

        bonafide = {

            "id": row.id,

            "bonafide_number": row.bonafide_number,

            "purpose": row.purpose or "",

            "date": format_date(row.date)

        }

        # =====================================================
        # STUDENT DATA
        # =====================================================

        student = {

            "name": row.name or "",

            "school_register_no": row.school_register_no or "",

            "class": getattr(row, "class", ""),

            "admission_date": format_date(
                row.admission_date
            ),

            "dob": format_date(row.dob),

            "caste": row.caste or "",

            "primary_mobile": row.primary_mobile or "",

            "email": row.student_email or ""

        }

        # =====================================================
        # SCHOOL DATA
        # =====================================================

        base_dir = os.path.abspath(
            os.path.dirname(__file__)
        )

        logo_absolute = ""
        watermark_absolute = ""

        if row.logo_path:

            logo_absolute = "file:///" + os.path.join(

                base_dir,
                "static",
                row.logo_path.replace(
                    "static/",
                    ""
                )

            ).replace("\\", "/")

        if row.watermark_path:

            watermark_absolute = "file:///" + os.path.join(

                base_dir,
                "static",
                row.watermark_path.replace(
                    "static/",
                    ""
                )

            ).replace("\\", "/")

        school = {

            "name": row.school_name or "",

            "address": row.address or "",

            "phone": row.phone or "",

            "email": row.school_email or "",

            "logo_path": logo_absolute,

            "watermark_path": watermark_absolute,

            "website": row.website or ""

        }

        # =====================================================
        # HTML TEMPLATE
        # =====================================================

        html = render_template(

            "clerk/bonafide_generate.html",

            student=student,

            bonafide=bonafide,

            school=school,

            is_pdf=True

        )

        # =====================================================
        # PDF FOLDER
        # =====================================================

        pdf_folder = os.path.join(

            "static",
            "generated_bonafide"

        )

        if not os.path.exists(pdf_folder):

            os.makedirs(pdf_folder)

        pdf_path = os.path.join(

            pdf_folder,

            f'bonafide_{bonafide["id"]}.pdf'

        )

        # =====================================================
        # PDF OPTIONS
        # =====================================================

        options = {

            "page-size": "A4",

            "margin-top": "5mm",

            "margin-right": "5mm",

            "margin-bottom": "5mm",

            "margin-left": "5mm",

            "encoding": "UTF-8",

            "enable-local-file-access": ""

        }

        # =====================================================
        # GENERATE PDF
        # =====================================================

        pdfkit.from_string(

            html,

            pdf_path,

            configuration=pdf_config,

            options=options

        )

        # =====================================================
        # 📧 AUTO SEND BONAFIDE PDF EMAIL
        # =====================================================

        try:

            student_email = student.get("email")

            if student_email:

                # =========================================
                # CHECK ALREADY SENT
                # =========================================

                cursor.execute("""

                    SELECT id
                    FROM bonafide_email_logs
                    WHERE school_id = ?
                    AND bonafide_id = ?

                """, (

                    row.school_id,
                    bonafide["id"]

                ))

                already_sent = cursor.fetchone()

                # =========================================
                # SEND ONLY ONCE
                # =========================================

                if not already_sent:

                    subject = (
                        f'Bonafide Certificate - {student["name"]}'
                    )

                    body = f"""

                    <div style="font-family:Arial;padding:20px;">

                        <h2 style="color:#14b8a6;">
                            Bonafide Certificate Generated
                        </h2>

                        <p>
                            Dear Parent/Student,
                        </p>

                        <p>
                            Your Bonafide Certificate
                            has been generated successfully.
                        </p>

                        <hr>

                        <p>
                            <b>Student Name:</b>
                            {student["name"]}
                        </p>

                        <p>
                            <b>Bonafide Number:</b>
                            {bonafide["bonafide_number"]}
                        </p>

                        <p>
                            <b>School:</b>
                            {school["name"]}
                        </p>

                        <hr>

                        <p>
                            Please find the Bonafide PDF attached.
                        </p>

                        <p>
                            Thank you,
                            <br>
                            <b>{school["name"]}</b>
                        </p>

                    </div>

                    """

            # =========================================
            # SEND MAIL
            # =========================================

            email_sent = send_email(

                student_email,
                subject,
                body,
                pdf_path,
                f"{bonafide['bonafide_number']}.pdf"

            )

            # =========================================
            # EMAIL SUCCESS
            # =========================================

            if email_sent == True:

                print("✅ BONAFIDE PDF EMAIL SENT")

                # =====================================
                # SAVE EMAIL LOG
                # =====================================

                cursor.execute("""

                    INSERT INTO bonafide_email_logs
                    (
                        school_id,
                        bonafide_id,
                        student_email
                    )
                    VALUES (?, ?, ?)

                """, (

                    row.school_id,
                    bonafide["id"],
                    student_email

                ))

                conn.commit()

            # =========================================
            # EMAIL FAILED
            # =========================================

            else:

                print(
                    "❌ BONAFIDE EMAIL FAILED:",
                    email_sent
                )

        except Exception as email_error:

            print(
                "❌ BONAFIDE EMAIL ERROR:",
                email_error
            )

        # =====================================================
        # RETURN PDF
        # =====================================================

        return send_file(

            pdf_path,

            as_attachment=True,

            download_name=f'{bonafide["bonafide_number"]}.pdf'

        )

    except Exception as e:

        print(
            "❌ BONAFIDE PDF ERROR:",
            e
        )

        return f"ERROR: {e}"

    finally:

        if cursor:
            cursor.close()

        if conn:
            conn.close()            
            
 # =========================================================
# 🔓 PUBLIC BONAFIDE VIEW (NO LOGIN REQUIRED)
# =========================================================
@app.route("/public/bonafide/<int:bid>")
def public_bonafide(bid):

    conn = None
    cursor = None

    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                b.*,
                s.name,
                s.school_register_no,
                s.class,
                s.admission_date,
                s.dob,
                s.caste,
                s.primary_mobile,

                sc.name AS school_name,
                sc.address,
                sc.phone,
                sc.email

            FROM bonafide b
            JOIN students s
                ON b.student_id = s.id
            JOIN schools sc
                ON b.school_id = sc.school_id
            WHERE b.id = ?
        """, (bid,))

        row = cursor.fetchone()

        if not row:
            return "Bonafide Not Found ❌"

        # ================= BONAFIDE DATA =================
        bonafide = {
            "bonafide_number": row.bonafide_number,
            "purpose": row.purpose or "",
            "date": format_date(row.date)
        }

        # ================= STUDENT DATA =================
        student = {
            "name": row.name or "",
            "school_register_no": row.school_register_no or "",
            "class": getattr(row, "class", ""),
            "admission_date": format_date(row.admission_date),
            "dob": format_date(row.dob),
            "caste": row.caste or "",
            "primary_mobile": row.primary_mobile or ""
        }

        # ================= SCHOOL DATA =================
        school = {
            "name": row.school_name or "",
            "address": row.address or "",
            "phone": row.phone or "",
            "email": row.email or ""
        }

        return render_template(
            "clerk/bonafide_generate.html",
            student=student,
            bonafide=bonafide,
            school=school,
            is_public=True
        )

    except Exception as e:
        print("❌ PUBLIC BONAFIDE ERROR:", e)
        return f"ERROR: {e}"

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
            
# =========================================================
#  IMPORT - EXPORT PAGE ROUTE
# =========================================================
@app.route("/clerk/import-export")
@login_required
def import_export_page():

    school = get_school_details(session.get("clerk_school_id"))

    if not school:
        return "School not found ❌"

    return render_template(
        "clerk/import_export.html",
        role="clerk",
        school_name=school["school_name"],
        school_udise=school["school_udise"],
        active_page="import_export",
    )

# =========================================================
# 📥 IMPORT STUDENTS FROM EXCEL (SAFE + ATOMIC)
# =========================================================
@app.route("/clerk/import-students", methods=["GET", "POST"])
@login_required
def import_students():

    if request.method == "GET":
        return redirect("/clerk/import-export")

    print("🔥 IMPORT STARTED")

    conn = None
    cursor = None

    try:
        file = request.files.get("file")

        # ================= FILE CHECK =================
        if not file:
            return "No file uploaded ❌"

        # ================= SAFE FILENAME =================
        filename = secure_filename(file.filename)

        # ================= EXTENSION CHECK =================
        if not filename.lower().endswith(".xlsx"):
            return "Only .xlsx files allowed ❌"
        

        school_id = session.get("clerk_school_id")

        if not school_id:
            return "School session missing ❌"

        # ================= READ EXCEL =================
        df = pd.read_excel(file)

        if df.empty:
            return "Excel file is empty ❌"

        # ================= LIMIT ROWS =================
        if len(df) > 5000:
            return "Maximum 5000 rows allowed ❌"

        # ================= NORMALIZE COLUMNS =================
        df.columns = df.columns.str.strip().str.lower()

        print("📊 Columns:", df.columns)

       # ================= REQUIRED COLUMN CHECK =================
        required_columns = ["name", "class"]

        for col in required_columns:
            if col not in df.columns:
                return f"Missing required column: {col} ❌"

        conn = get_connection()
        cursor = conn.cursor()

        inserted_count = 0

        for _, row in df.iterrows():

            # ================= CLEAN NULLS =================
            row = row.where(pd.notnull(row), None)

            # ================= BASIC REQUIRED =================
            name = row.get("name")
            class_name = row.get("class")

            # ================= SKIP INVALID =================
            if not name or not class_name:
                print("⚠️ Row skipped (missing required data)")
                continue

            # ================= NEW FIELDS =================
            school_register_no = row.get("school_register_no")

            student_uid = row.get("student_uid")
            if student_uid:
                student_uid = str(student_uid).split(".")[0].strip()

            apaar_id = row.get("apaar_id")
            if apaar_id:
                apaar_id = str(apaar_id).split(".")[0].strip()

           # ================= DATE FIX =================
            dob = row.get("dob")

            if dob:
                try:
                    if hasattr(dob, "strftime"):
                        dob = dob.strftime("%Y-%m-%d")
                    else:
                        dob = pd.to_datetime(
                            str(dob),
                            dayfirst=True
                        ).strftime("%Y-%m-%d")
                except:
                    dob = None


            admission_date = row.get("admission_date")

            if admission_date:
                try:
                    if hasattr(admission_date, "strftime"):
                        admission_date = admission_date.strftime("%Y-%m-%d")
                    else:
                        admission_date = pd.to_datetime(
                            str(admission_date),
                            dayfirst=True
                        ).strftime("%Y-%m-%d")
                except:
                    admission_date = None

            # ================= OTHER FIELDS =================
            caste = row.get("caste")
            father_name = row.get("father_name")
            mother_name = row.get("mother_name")
            aadhaar = row.get("aadhaar")

            birth_place = row.get("birth_place")
            nationality = row.get("nationality")
            mother_tongue = row.get("mother_tongue")
            religion = row.get("religion")

            city = row.get("city")
            taluka = row.get("taluka")
            district = row.get("district")
            state = row.get("state")

            section = row.get("section")
            previous_school = row.get("previous_school")

            last_exam = row.get("last_exam")
            result_status = row.get("result_status")

            progress = row.get("progress")
            conduct = row.get("conduct")

            primary_mobile = row.get("primary_mobile")
            alternate_mobile = row.get("alternate_mobile")

            occupation = row.get("occupation")
            income = row.get("income")
            if income:
                try:
                    income = int(float(income))
                except:
                    income = None

            guardian_name = row.get("guardian_name")
            guardian_mobile = row.get("guardian_mobile")

            # ================= AADHAAR VALIDATION =================
            if aadhaar:
                aadhaar = str(aadhaar).strip()

                if not aadhaar.isdigit() or len(aadhaar) != 12:
                    print("⚠️ Invalid Aadhaar skipped")
                    continue

            # ================= MOBILE CLEANUP =================
            if primary_mobile:
                primary_mobile = str(primary_mobile).split(".")[0].strip()

            if alternate_mobile:
                alternate_mobile = str(alternate_mobile).split(".")[0].strip()

            if guardian_mobile:
                guardian_mobile = str(guardian_mobile).split(".")[0].strip()

            print("Processing:", name)


# ================= DUPLICATE CHECK (FIXED) =================
            existing_student = None

            # check aadhaar only if valid and exists
            if aadhaar:
                cursor.execute("""
                    SELECT TOP 1 id
                    FROM students
                    WHERE school_id = ?
                    AND aadhaar = ?
                """, (
                    school_id,
                    aadhaar
                ))
                existing_student = cursor.fetchone()

            # check student uid only if aadhaar not matched
            if not existing_student and student_uid:
                cursor.execute("""
                    SELECT TOP 1 id
                    FROM students
                    WHERE school_id = ?
                    AND student_uid = ?
                """, (
                    school_id,
                    student_uid
                ))
                existing_student = cursor.fetchone()

            # skip only real duplicates
            if existing_student:
                print(
                    "⚠️ Duplicate student skipped:",
                    name,
                    aadhaar,
                    student_uid
                )
                continue
            # ================= SAFE ATOMIC ADMISSION =================
            admission_no = generate_admission_no(school_id)


               # ================= INSERT =================
            cursor.execute("""
                INSERT INTO students (
                    school_id,
                    school_register_no,
                    name,
                    father_name,
                    mother_name,
                    student_uid,
                    aadhaar,
                    apaar_id,
                    dob,
                    birth_place,
                    nationality,
                    mother_tongue,
                    religion,
                    caste,
                    city,
                    taluka,
                    district,
                    state,
                    admission_no,
                    admission_date,
                    [class],
                    section,
                    previous_school,
                    last_exam,
                    result_status,
                    progress,
                    conduct,
                    primary_mobile,
                    alternate_mobile,
                    occupation,
                    income,
                    guardian_name,
                    guardian_mobile
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                school_id,
                school_register_no,
                name,
                father_name,
                mother_name,
                student_uid,
                aadhaar,
                apaar_id,
                dob,
                birth_place,
                nationality,
                mother_tongue,
                religion,
                caste,
                city,
                taluka,
                district,
                state,
                admission_no,
                admission_date,
                class_name,
                section,
                previous_school,
                last_exam,
                result_status,
                progress,
                conduct,
                primary_mobile,
                alternate_mobile,
                occupation,
                income,
                guardian_name,
                guardian_mobile
            ))

            inserted_count += 1

        conn.commit()

        print("✅ IMPORT SUCCESS:", inserted_count)

        return redirect(
            f"/clerk/import-export?success={inserted_count}"
        )

    except Exception as e:

        if conn:
            conn.rollback()

        print("❌ IMPORT ERROR:", e)
        return f"Error: {str(e)}"

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


# =========================================================
# 📤 EXPORT STUDENTS TO EXCEL (SAFE + FIXED)
# =========================================================
@app.route("/clerk/export-students")
@login_required
def export_students():

    conn = None
    cursor = None

    try:
        import io
        from datetime import datetime

        cls = (request.args.get("class") or "").strip()
        month = (request.args.get("month") or "").strip()
        year = (request.args.get("year") or "").strip()

        school_id = session.get("clerk_school_id")

        if not school_id:
            return "School not found ❌"

        # ================= MONTH VALIDATION =================
        if month:
            if not month.isdigit() or int(month) < 1 or int(month) > 12:
                return "Invalid month filter ❌"

        # ================= YEAR VALIDATION =================
        if year:
            if not year.isdigit():
                return "Invalid year filter ❌"

        conn = get_connection()
        cursor = conn.cursor()

        query = """
                SELECT
                    school_register_no,
                    name,
                    father_name,
                    mother_name,
                    student_uid,
                    aadhaar,
                    apaar_id,
                    dob,
                    birth_place,
                    nationality,
                    mother_tongue,
                    religion,
                    caste,
                    city,
                    taluka,
                    district,
                    state,
                    admission_no,
                    admission_date,
                    [class] AS class,
                    section,
                    previous_school,
                    last_exam,
                    result_status,
                    progress,
                    conduct,
                    primary_mobile,
                    alternate_mobile,
                    occupation,
                    income,
                    guardian_name,
                    guardian_mobile
                FROM students
                WHERE school_id = ?
                """

        params = [school_id]

        # ================= FILTER CLASS =================
        if cls:
            query += " AND [class] = ?"
            params.append(str(cls))

        cursor.execute(query, params)

        rows = cursor.fetchall()

        columns = [col[0] for col in cursor.description]
        students = [dict(zip(columns, row)) for row in rows]

        # ================= FILTER MONTH / YEAR =================
        if month or year:

            filtered = []

            for s in students:

                date = s.get("admission_date")

                if not date:
                    continue

                try:
                    if isinstance(date, str):
                         # support both formats
                        try:
                            date = datetime.strptime(
                                date,
                                "%Y-%m-%d"
                            )
                        except Exception:
                            date = datetime.strptime(
                                date,
                                "%d-%m-%Y"
                            )

                    if month and int(month) != date.month:
                        continue

                    if year and int(year) != date.year:
                        continue

                except Exception:
                    continue

                filtered.append(s)

            students = filtered

        # ================= NO DATA =================
        if not students:
            return "No data found for selected filters ❌"

        # ================= FORMAT DATES =================
        def format_date(d):
            if not d:
                return ""

            try:
                return d.strftime("%d-%m-%Y")
            except Exception:
                return str(d)
            
         # ================= EXCEL INJECTION PROTECTION =================
        def sanitize_excel(value):

            if isinstance(value, str):

                value = value.strip()

                # Prevent Excel formula execution
                if value.startswith(("=", "+", "-", "@")):
                    return "'" + value

            return value

        for s in students:

            # Format dates
            s["dob"] = format_date(s.get("dob"))
            s["admission_date"] = format_date(s.get("admission_date"))

             # SANITIZE ALL VALUES
            for key in s:
                s[key] = sanitize_excel(s[key])

        # ================= CREATE EXCEL =================
        df = pd.DataFrame(students)

        output = io.BytesIO()
        df.to_excel(output, index=False)

        output.seek(0)

        return send_file(
            output,
            as_attachment=True,
            download_name="students.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except Exception as e:
        print("❌ EXPORT ERROR:", e)
        return f"Export Failed ❌ {str(e)}"

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
            
                
 
# =========================================================
# 🚧 COMING SOON PAGE ROUTE (CLERK SAFE)
# PURPOSE:
# Show under-development pages for clerk panel
# Uses clerk session only (safe for multi-login)
# =========================================================

@app.route("/coming-soon/<feature>")
@login_required
def coming_soon(feature):

    try:
        clerk_school_id = session.get("clerk_school_id")

        if not clerk_school_id:
            return "School session missing ❌"

        feature = feature.lower().strip()

        feature_names = {
            "attendance": "Attendance Management",
            "marks": "Marks & Results",
            "teachers": "Teacher Management",
            "fees": "Fee Management",
            "timetable": "Timetable",
            "notice-board": "Notice Board"
        }

        # FIXED: invalid feature block
        if feature not in feature_names:
            return "Invalid feature ❌"

        school = get_school_details(clerk_school_id)

        # FIXED: school existence check
        if not school:
            return "School not found ❌"

        return render_template(
            "features/coming_soon.html",
            feature=feature_names.get(feature),

            role="clerk",

            school_name=school["school_name"],
            school_udise=school["school_udise"],
            active_page=""
        )

    except Exception as e:
        print("❌ COMING SOON ERROR:", e)
        return f"ERROR: {e}"
    
    
# =========================================================
# 📊 ATTENDANCE MODULE
# =========================================================

@app.route("/clerk/attendance")
@login_required
def attendance_dashboard():

    return redirect(
        url_for(
            "coming_soon",
            feature="attendance"
        )
    )
# =========================================================
#  MARKS & RESULTS MODULE
# =========================================================
@app.route("/clerk/results")
@login_required
def results_dashboard():

    return redirect(
        url_for(
            "coming_soon",
            feature="marks"
        )
    )
# =========================================================
# TEACHERS MODULE
# =========================================================
@app.route("/clerk/teachers")
@login_required
def teachers_dashboard():

    return redirect(
        url_for(
            "coming_soon",
            feature="teachers"
        )
    )

# =========================================================
# 💰 FEE MANAGEMENT
# =========================================================

@app.route("/clerk/fees")
@login_required
def fee_dashboard():

    return redirect(
        url_for(
            "coming_soon",
            feature="fees"
        )
    )
# =========================================================
# TIMETABLE MODULE
# =========================================================
@app.route("/clerk/timetable")
@login_required
def timetable_dashboard():

    return redirect(
        url_for(
            "coming_soon",
            feature="timetable"
        )
    )
# =========================================================
# NOTICE BOARD MODULE
# =========================================================
@app.route("/clerk/notice-board")
@login_required
def notice_board_dashboard():

    return redirect(
        url_for(
            "coming_soon",
            feature="notice-board"
        )
    )

# =========================================================
# 🚀 RUN APP
# =========================================================
if __name__ == '__main__':
    app.run(debug=True)