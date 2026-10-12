import os

import pymysql
from flask import (
    Flask,
    flash,
    redirect,
    render_template,
    request,
    session,
)
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import (
    check_password_hash,
    generate_password_hash,
)

from db import get_db_connection, init_db
from utils import (
    UPLOAD_FOLDER,
    delete_file_from_s3,
    delete_files_from_s3,
    generate_presigned_url,
    save_file,
)


# =========================
# APPLICATION CONFIGURATION
# =========================

app = Flask(__name__)

app.config["SECRET_KEY"] = os.environ.get(
    "SECRET_KEY",
    "local-development-only-key",
)

csrf = CSRFProtect(app)


# =========================
# HOME PAGE
# =========================

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
                (user_id,),
            )
            user = cursor.fetchone()
        finally:
            cursor.close()
            connection.close()

        # Clear the session if the account no longer exists in the database.
        if not user:
            session.pop("user_id", None)

    return render_template(
        "index.html",
        user=user,
    )


# =========================
# REGISTER
# =========================

@app.route("/register", methods=["POST"])
def register():
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    raw_password = request.form.get("password", "")

    phone = request.form.get("phone", "").strip()
    gender = request.form.get("gender")
    course = request.form.get("course")

    if not name or not email or not raw_password:
        flash("Name, email and password are required!")
        return redirect("/")

    # Check for existing email before uploading files to avoid orphaned S3 objects
    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            "SELECT id FROM registrations WHERE email = %s",
            (email,),
        )
        if cursor.fetchone():
            flash("Email already exists!")
            return redirect("/")
    finally:
        cursor.close()
        connection.close()

    # Hash the password before storing
    hashed_password = generate_password_hash(raw_password)

    # Upload files directly to Amazon S3
    try:
        photo = save_file(request, "photo")
        audio = save_file(request, "audio")
        video = save_file(request, "video")
        document = save_file(request, "document")
    except Exception as e:
        flash(f"File upload failed: {str(e)}")
        return redirect("/")

    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            INSERT INTO registrations
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
                document
            )
            VALUES
            (
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s
            )
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
            ),
        )

        user_id = cursor.lastrowid
        session["user_id"] = user_id
        flash("Registration successful!")

    except pymysql.err.IntegrityError:
        flash("Email already exists!")

    finally:
        cursor.close()
        connection.close()

    return redirect("/")


# =========================
# LOGIN
# =========================

@app.route("/login", methods=["POST"])
def login():
    email = request.form.get("email", "").strip()
    raw_password = request.form.get("password", "")

    if not email or not raw_password:
        flash("Please enter your email and password!")
        return redirect("/")

    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT id, email, password
            FROM registrations
            WHERE email = %s
            """,
            (email,),
        )
        users = cursor.fetchall()
    finally:
        cursor.close()
        connection.close()

    # Verify the submitted password against the stored hash
    matched_user = None
    for u in users:
        if check_password_hash(u["password"], raw_password):
            matched_user = u
            break

    if matched_user:
        session["user_id"] = matched_user["id"]
        flash("Login successful!")
    else:
        flash("Invalid email or password!")

    return redirect("/")


# =========================
# UPDATE PROFILE
# =========================

@app.route("/update", methods=["POST"])
def update():
    user_id = session.get("user_id")

    if not user_id:
        flash("Please login first.")
        return redirect("/")

    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            "SELECT * FROM registrations WHERE id = %s",
            (user_id,),
        )
        user = cursor.fetchone()

        if not user:
            session.pop("user_id", None)
            flash("User not found.")
            return redirect("/")

        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        new_password = request.form.get("password", "").strip()

        if not name or not email:
            flash("Name and email are required!")
            return redirect("/")

        cursor.execute(
            "SELECT id FROM registrations WHERE email = %s AND id != %s",
            (email, user_id),
        )
        if cursor.fetchone():
            flash("That email address is already in use.")
            return redirect("/")

        phone = request.form.get("phone", "").strip()
        gender = request.form.get("gender")
        course = request.form.get("course")

        # Preserve the existing hash unless a new plaintext password is provided
        if (
            new_password
            and new_password != user["password"]
            and not new_password.startswith(("scrypt:", "pbkdf2:", "argon2:"))
        ):
            password = generate_password_hash(new_password)
        else:
            password = user["password"]

        # Upload new files to Amazon S3
        try:
            new_photo = save_file(request, "photo")
            new_audio = save_file(request, "audio")
            new_video = save_file(request, "video")
            new_document = save_file(request, "document")
        except Exception as e:
            flash(f"File upload failed: {str(e)}")
            return redirect("/")

        # If a replacement file was uploaded, safely remove the old file from S3
        if new_photo and user.get("photo"):
            delete_file_from_s3(user["photo"])
        if new_audio and user.get("audio"):
            delete_file_from_s3(user["audio"])
        if new_video and user.get("video"):
            delete_file_from_s3(user["video"])
        if new_document and user.get("document"):
            delete_file_from_s3(user["document"])

        # Preserve existing files when no replacement was uploaded
        photo = new_photo or user["photo"]
        audio = new_audio or user["audio"]
        video = new_video or user["video"]
        document = new_document or user["document"]

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
            ),
        )

        flash("Profile updated successfully!")

    except pymysql.err.IntegrityError:
        flash("That email address is already in use.")

    finally:
        cursor.close()
        connection.close()

    return redirect("/")


# =========================
# DELETE ACCOUNT
# =========================

@app.route("/delete", methods=["POST"])
def delete():
    user_id = session.get("user_id")

    if not user_id:
        flash("Please login first.")
        return redirect("/")

    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        # Retrieve user file keys before deleting the record
        cursor.execute(
            "SELECT photo, audio, video, document FROM registrations WHERE id = %s",
            (user_id,),
        )
        user_files = cursor.fetchone()

        cursor.execute(
            "DELETE FROM registrations WHERE id = %s",
            (user_id,),
        )

        session.pop("user_id", None)

        # Safely remove associated files from Amazon S3
        if user_files:
            file_keys = [
                user_files.get("photo"),
                user_files.get("audio"),
                user_files.get("video"),
                user_files.get("document"),
            ]
            delete_files_from_s3(file_keys)

        flash("Account deleted successfully!")

    finally:
        cursor.close()
        connection.close()

    return redirect("/")


# =========================
# LOGOUT
# =========================

@app.route("/logout")
def logout():
    session.pop("user_id", None)
    flash("Logged out successfully!")
    return redirect("/")


# =========================
# SERVE UPLOADED FILES VIA S3 PRESIGNED URLS
# =========================

@app.route("/uploads/<filename>")
def uploaded_file(filename):
    """
    Secure file access route.
    Authenticates the user, verifies ownership of the requested file,
    and redirects to a temporary Amazon S3 presigned URL.
    """
    user_id = session.get("user_id")

    if not user_id:
        flash("Please login to access files.")
        return redirect("/")

    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            "SELECT photo, audio, video, document FROM registrations WHERE id = %s",
            (user_id,),
        )
        user_record = cursor.fetchone()
    finally:
        cursor.close()
        connection.close()

    if not user_record:
        session.pop("user_id", None)
        flash("User account not found.")
        return redirect("/")

    allowed_files = {
        user_record.get("photo"),
        user_record.get("audio"),
        user_record.get("video"),
        user_record.get("document"),
    }

    # Verify that the requested file belongs to the logged-in user
    if not filename or filename not in allowed_files:
        flash("Access denied: You do not have permission to access this file.")
        return redirect("/")

    as_attachment = request.args.get("download") in ("1", "true", "True")
    presigned_url = generate_presigned_url(
        filename,
        expiration=3600,
        as_attachment=as_attachment,
    )

    if not presigned_url:
        flash("Unable to access file.")
        return redirect("/")

    return redirect(presigned_url)


# =========================
# DATABASE INITIALIZATION ON STARTUP
# =========================

if not os.environ.get("PYTEST_CURRENT_TEST"):
    try:
        init_db()
    except Exception as err:
        print(f"Notice: Database initialization deferred ({err}).")


# =========================
# START APPLICATION
# =========================

if __name__ == "__main__":
    init_db()

    debug_mode = os.getenv("FLASK_DEBUG", "0") == "1"

    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=debug_mode,
    )
