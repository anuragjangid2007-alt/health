import os
from functools import wraps

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
)
from medical_search import search_medical_sources
from dotenv import load_dotenv
from werkzeug.security import (
    generate_password_hash,
    check_password_hash,
)

import database
from verifier import verify_question
from ai_engine import generate_answer


# Load environment variables from .env
load_dotenv()

# Create Flask application
app = Flask(__name__)

app.config["SECRET_KEY"] = os.getenv(
    "FLASK_SECRET_KEY",
    "local-development-key-change-before-deployment",
)

app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"


# Login protection
def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in first.", "warning")
            return redirect(url_for("login"))

        return view(*args, **kwargs)

    return wrapped_view


# Home page
@app.route("/")
def index():
    return render_template("index.html")


# User registration
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not name or not email or not password:
            flash("Please fill in all required fields.", "danger")
            return render_template("register.html")

        if len(password) < 8:
            flash(
                "Password must contain at least 8 characters.",
                "danger",
            )
            return render_template("register.html")

        try:
            user_id = database.create_user(
                name,
                email,
                generate_password_hash(password),
            )
        except Exception:
            app.logger.exception("Registration failed")
            flash(
                "Registration failed. This email may already be registered.",
                "danger",
            )
            return render_template("register.html")

        session.clear()
        session["user_id"] = user_id

        flash("Account created successfully!", "success")
        return redirect(url_for("dashboard"))

    return render_template("register.html")


# User login
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = database.get_user_by_email(email)

        if user and check_password_hash(
            user["password_hash"],
            password,
        ):
            session.clear()
            session["user_id"] = user["id"]

            flash("Welcome back!", "success")
            return redirect(url_for("dashboard"))

        flash("Incorrect email or password.", "danger")

    return render_template("login.html")


# User logout
@app.route("/logout")
def logout():
    session.clear()

    flash("You have been logged out.", "info")
    return redirect(url_for("index"))


# Dashboard
@app.route("/dashboard")
@login_required
def dashboard():
    user = database.get_user_by_id(session["user_id"])
    history = database.get_user_history(
        session["user_id"],
        limit=5,
    )

    return render_template(
        "dashboard.html",
        user=user,
        history=history,
        answer=None,
        evidence=[],
        question="",
        mode=None,
        status=None,
    )


# Healthcare question and evidence verification
@app.route("/ask", methods=["POST"])
@login_required
def ask():
    question = request.form.get("question", "").strip()

    if not question:
        flash(
            "Please enter a healthcare question.",
            "warning",
        )
        return redirect(url_for("dashboard"))

    if len(question) > 1000:
        flash(
            "Please keep your question under 1000 characters.",
            "warning",
        )
        return redirect(url_for("dashboard"))

    user_id = session["user_id"]

    # Search the local healthcare evidence database
    verification = verify_question(question)

    local_evidence = verification.get("evidence", [])

    online_evidence = search_medical_sources(question)

    evidence = local_evidence + online_evidence

    answer, mode = generate_answer(question, evidence)

    # Display an appropriate evidence status
    status = verification.get(
        "message",
        "Potential source match — review required",
    )

    if evidence:
        evidence_title = ", ".join(
            str(item.get("title", "Untitled source"))
            for item in evidence
        )
    else:
        evidence_title = None

    # Save the question and response in user history
    database.save_history(
        user_id,
        question,
        answer,
        status,
        evidence_title,
    )

    # Refresh dashboard information
    user = database.get_user_by_id(user_id)
    history = database.get_user_history(
        user_id,
        limit=5,
    )

    return render_template(
        "dashboard.html",
        user=user,
        history=history,
        answer=answer,
        evidence=evidence,
        question=question,
        mode=mode,
        status=status,
    )


# User profile
@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    user_id = session["user_id"]

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        age_text = request.form.get("age", "").strip()
        notes = request.form.get("profile_notes", "").strip()

        if not name:
            flash("Name is required.", "danger")
            return redirect(url_for("profile"))

        if len(notes) > 500:
            flash(
                "Profile notes must be 500 characters or fewer.",
                "warning",
            )
            return redirect(url_for("profile"))

        age = None

        if age_text:
            try:
                age = int(age_text)

                if age < 1 or age > 120:
                    raise ValueError

            except ValueError:
                flash("Please enter a valid age.", "danger")
                return redirect(url_for("profile"))

        database.update_profile(
            user_id,
            name,
            age,
            notes,
        )

        flash("Profile updated.", "success")
        return redirect(url_for("profile"))

    user = database.get_user_by_id(user_id)

    return render_template(
        "profile.html",
        user=user,
    )


# Complete search history
@app.route("/history")
@login_required
def history():
    records = database.get_user_history(
        session["user_id"]
    )

    return render_template(
        "history.html",
        records=records,
    )


# Individual history record
@app.route("/history/<int:history_id>")
@login_required
def history_detail(history_id):
    record = database.get_history_item(
        session["user_id"],
        history_id,
    )

    if record is None:
        flash("History item not found.", "warning")
        return redirect(url_for("history"))

    return render_template(
        "history_detail.html",
        record=record,
    )


# Initialize the database
with app.app_context():
    database.init_db()


# Start the application
if __name__ == "__main__":
    app.run(debug=True)