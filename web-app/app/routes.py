"""Flask routes for the audio notes web application."""

from datetime import datetime
from io import BytesIO

from bson import ObjectId
from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

from .db import get_db, get_fs

bp = Blueprint("main", __name__)


# Helper function to check if user is logged in
def login_required(f):
    """Decorator to require login for routes."""
    from functools import wraps

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to access this page.", "error")
            return redirect(url_for("main.login"))
        return f(*args, **kwargs)

    return decorated_function


@bp.route("/")
def index():
    """Redirect root to dashboard if logged in, otherwise to login."""
    if "user_id" in session:
        return redirect(url_for("main.dashboard"))
    return redirect(url_for("main.login"))


@bp.route("/login", methods=["GET", "POST"])
def login():
    """Login page and handler."""
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username or not password:
            flash("Please provide both username and password.", "error")
            return render_template("login.html", username=username)

        db = get_db()
        user = db.users.find_one({"email": username})

        if not user:
            # Try finding by username instead
            user = db.users.find_one({"username": username})

        if user and check_password_hash(user.get("password_hash", ""), password):
            session["user_id"] = str(user["_id"])
            session["username"] = user.get("username", "User")
            flash("Login successful!", "success")
            return redirect(url_for("main.dashboard"))

        flash("Invalid credentials. Please try again.", "error")
        return render_template("login.html", username=username)

    return render_template("login.html")


@bp.route("/signup", methods=["GET"])
def signup():
    """Display signup page."""
    return render_template("signup.html")


@bp.route("/register", methods=["POST"])
def register():
    """Handle user registration."""
    username = request.form.get("username", "").strip()
    email = request.form.get("email", "").strip()

    if not username or not email:
        flash("Username and email are required.", "error")
        return render_template("signup.html", username=username, email=email)

    # Generate a default password (in production, send via email or use better flow)
    default_password = "password123"

    db = get_db()

    # Check if user already exists
    if db.users.find_one({"email": email}):
        flash("Email already registered.", "error")
        return render_template("signup.html", username=username, email=email)

    if db.users.find_one({"username": username}):
        flash("Username already taken.", "error")
        return render_template("signup.html", username=username, email=email)

    # Create user
    password_hash = generate_password_hash(default_password)
    user_doc = {
        "username": username,
        "email": email,
        "password_hash": password_hash,
        "created_at": datetime.utcnow(),
    }
    result = db.users.insert_one(user_doc)

    session["user_id"] = str(result.inserted_id)
    session["username"] = username

    flash(
        f"Account created! Your password is: {default_password} (change it later)",
        "success",
    )
    return redirect(url_for("main.dashboard"))


@bp.route("/logout")
def logout():
    """Log out the current user."""
    session.clear()
    flash("Logged out successfully.", "success")
    return redirect(url_for("main.login"))


@bp.route("/dashboard")
@login_required
def dashboard():
    """Main dashboard showing all recordings."""
    db = get_db()
    user_id = ObjectId(session["user_id"])

    # Get all recordings for this user
    recordings = list(
        db.recordings.find({"user_id": user_id}).sort("created_at", -1).limit(50)
    )

    # Enrich with note data
    for rec in recordings:
        note = db.notes.find_one({"recording_id": rec["_id"]})
        if note:
            rec["summary"] = note.get("summary", "")
            rec["keywords"] = note.get("keywords", [])
        else:
            rec["summary"] = ""
            rec["keywords"] = []

    return render_template("dashboard.html", recordings=recordings)


@bp.route("/upload", methods=["GET", "POST"])
@login_required
def upload():
    """Upload or record audio page."""
    if request.method == "POST":
        if "file" not in request.files:
            return {"error": "No file provided"}, 400

        file = request.files["file"]
        if file.filename == "":
            return {"error": "Empty filename"}, 400

        # Save to GridFS
        fs = get_fs()
        filename = secure_filename(file.filename) if file.filename else "recording.webm"
        file_id = fs.put(file.read(), filename=filename)

        # Create recording document
        db = get_db()
        user_id = ObjectId(session["user_id"])
        recording_doc = {
            "user_id": user_id,
            "file_id": file_id,
            "audio_gridfs_id": file_id,
            "filename": filename,
            "status": "pending",
            "created_at": datetime.utcnow(),
        }
        recording_id = db.recordings.insert_one(recording_doc).inserted_id

        return {"success": True, "recording_id": str(recording_id)}, 200

    return render_template("upload.html")


@bp.route("/recording/<recording_id>")
@login_required
def recording_detail(recording_id):
    """Show detail view for a single recording."""
    db = get_db()
    user_id = ObjectId(session["user_id"])

    try:
        rec_id = ObjectId(recording_id)
    except Exception:  # pylint: disable=broad-exception-caught
        flash("Invalid recording ID.", "error")
        return redirect(url_for("main.dashboard"))

    recording = db.recordings.find_one({"_id": rec_id, "user_id": user_id})
    if not recording:
        flash("Recording not found.", "error")
        return redirect(url_for("main.dashboard"))

    # Get associated note
    note = db.notes.find_one({"recording_id": rec_id})

    # Generate audio URL
    file_id = recording.get("audio_gridfs_id") or recording.get("file_id")
    audio_url = url_for("main.serve_audio", file_id=str(file_id)) if file_id else None

    return render_template(
        "detail.html", recording=recording, note=note, audio_url=audio_url
    )


@bp.route("/audio/<file_id>")
@login_required
def serve_audio(file_id):
    """Serve audio file from GridFS."""
    try:
        fs = get_fs()
        grid_out = fs.get(ObjectId(file_id))
        return send_file(
            BytesIO(grid_out.read()),
            mimetype="audio/webm",
            as_attachment=False,
            download_name="audio.webm",
        )
    except Exception as e:  # pylint: disable=broad-exception-caught
        return {"error": f"Audio file not found: {str(e)}"}, 404
