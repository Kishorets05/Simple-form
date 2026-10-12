
import os

import pymysql
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    session,
    send_from_directory,
    flash,
    url_for,
)
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import generate_password_hash, check_password_hash

from db import get_db_connection, init_db
from utils import save_file, UPLOAD_FOLDER


# --------------------------------------------------
# FLASK CONFIGURATION
# --------------------------------------------------

app = Flask(__name__)

app.config["SECRET_KEY"] = os.environ.get(
    "SECRET_KEY",
    "local-development-only-key"
)

csrf = CSRFProtect(app)


# --------------------------------------------------
# HOME PAGE / USER PROFILE
# --------------------------------------------------

@app.route("/")
def index():
    user_id = session.get("user_id")
    user = None

    if user_id:
        connection = get_db_connection()
        cursor = connection.cursor()

        try:
            cursor.execute(
                "SELECT * FROM registrations WHERE id = %s",
                (user_id,)
            )
            user = cursor.fetchone()

        finally:
            cursor.close()
            connection.close()

        # Clear the session if the user no longer exists.
        if not user:
            session.pop("user_id", None)

    return render_template("index.html", user=user)


# --------------------------------------------------
# REGISTER
# --------------------------------------------------

@app.route("/register", methods=["POST"])
def register():
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    raw_password = request.form.get("password", "")
    phone = request.form.get("phone", "").strip()
    gender = request.form.get("gender")
    course = request.form.get("course")

    # Validate required fields.
    if not name or not email or not raw_password:
        flash("Name, email and password are required!")
        return redirect(url_for("index"))

    # Hash the password before saving it.
    hashed_password = generate_password_hash(raw_password)

    # Save uploaded files.
    photo = save_file(request, "photo")
    audio = save_file(request, "audio")
    video = save_file(request, "video")
    document = save_file(request, "document")

    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            INSERT INTO registrations
            (
                name, email, password, phone, gender, course,
                photo, audio, video, document
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                name,
                email,
                hashed_password,
                phone,
                gender,
                course,
                photo,
                audio,
                video,
                document,
            )
        )

        # Log in the newly registered user.
        session.clear()
        session["user_id"] = cursor.lastrowid

        flash("Registration successful!")

    except pymysql.err.IntegrityError:
        flash("Email already exists!")

    finally:
        cursor.close()
        connection.close()

    return redirect(url_for("index"))


# --------------------------------------------------
# LOGIN
# --------------------------------------------------

@app.route("/login", methods=["POST"])
def login():
    email = request.form.get("email", "").strip().lower()
    raw_password = request.form.get("password", "")

    if not email or not raw_password:
        flash("Please enter your email and password!")
        return redirect(url_for("index"))

    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT id, email, password
            FROM registrations
            WHERE email = %s
            """,
            (email,)
        )

        user = cursor.fetchone()

    finally:
        cursor.close()
        connection.close()

    # Compare the entered password against its stored hash.
    if user and check_password_hash(user["password"], raw_password):
        session.clear()
        session["user_id"] = user["id"]

        flash("Login successful!")

    else:
        flash("Invalid email or password!")

    return redirect(url_for("index"))


# --------------------------------------------------
# UPDATE PROFILE
# --------------------------------------------------

@app.route("/update", methods=["POST"])
def update():
    user_id = session.get("user_id")

    if not user_id:
        flash("Please login first.")
        return redirect(url_for("index"))

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    new_password = request.form.get("password", "")
    phone = request.form.get("phone", "").strip()
    gender = request.form.get("gender")
    course = request.form.get("course")

    if not name or not email:
        flash("Name and email are required!")
        return redirect(url_for("index"))

    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        # Retrieve the existing profile.
        cursor.execute(
            "SELECT * FROM registrations WHERE id = %s",
            (user_id,)
        )
        user = cursor.fetchone()

        if not user:
            session.clear()
            flash("User not found. Please register again.")
            return redirect(url_for("index"))

        # Change the password only when a new password is supplied.
        if new_password:
            password = generate_password_hash(new_password)
        else:
            # Preserve the existing password hash.
            password = user["password"]

        # Preserve existing files when no replacement is uploaded.
        photo = save_file(request, "photo") or user["photo"]
        audio = save_file(request, "audio") or user["audio"]
        video = save_file(request, "video") or user["video"]
        document = save_file(request, "document") or user["document"]

        cursor.execute(
            """
            UPDATE registrations
            SET
                name = %s,
                email = %s,
                password = %s,
                phone = %s,
                gender = %s,
                course = %s,
                photo = %s,
                audio = %s,
                video = %s,
                document = %s
            WHERE id = %s
            """,
            (
                name,
                email,
                password,
                phone,
                gender,
                course,
                photo,
                audio,
                video,
                document,
                user_id,
            )
        )

        flash("Profile updated successfully!")

    except pymysql.err.IntegrityError:
        flash("That email address is already in use.")

    finally:
        cursor.close()
        connection.close()

    return redirect(url_for("index"))


# --------------------------------------------------
# DELETE ACCOUNT
# --------------------------------------------------

@app.route("/delete", methods=["POST"])
def delete():
    user_id = session.get("user_id")

    if not user_id:
        flash("Please login first.")
        return redirect(url_for("index"))

    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            "DELETE FROM registrations WHERE id = %s",
            (user_id,)
        )

        session.clear()
        flash("Account deleted successfully!")

    finally:
        cursor.close()
        connection.close()

    return redirect(url_for("index"))


# --------------------------------------------------
# LOGOUT
# --------------------------------------------------

@app.route("/logout", methods=["GET", "POST"])
def logout():
    session.clear()
    flash("Logged out successfully!")

    return redirect(url_for("index"))


# --------------------------------------------------
# SERVE UPLOADED FILES
# --------------------------------------------------

@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)


# --------------------------------------------------
# APPLICATION STARTUP
# --------------------------------------------------

if __name__ == "__main__":
    init_db()

    debug_mode = os.getenv("FLASK_DEBUG", "0") == "1"

    app.run(
        host="127.0.0.1",
        port=int(os.getenv("PORT", "5000")),
        debug=debug_mode,
    )
