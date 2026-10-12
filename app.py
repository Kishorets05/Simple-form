
import os

import pymysql
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    session,
    send_from_directory,
    flash
)
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

from db import get_db_connection, init_db
from utils import save_file, UPLOAD_FOLDER


# =========================
# APPLICATION CONFIGURATION
# =========================

app = Flask(__name__)

app.config["SECRET_KEY"] = os.environ.get(
    "SECRET_KEY",
    "local-development-only-key"
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
                (user_id,)
            )

            user = cursor.fetchone()

        finally:
            cursor.close()
            connection.close()

        # Clear the session if the account no longer exists.
        if not user:
            session.pop("user_id", None)

    return render_template(
        "index.html",
        user=user
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

    # Hash the password before storing it.
    hashed_password = generate_password_hash(raw_password)

    photo = save_file(request, "photo")
    audio = save_file(request, "audio")
    video = save_file(request, "video")
    document = save_file(request, "document")

    connection = get_db_connection()
    cursor = connection.cursor()

    try:

        cursor.execute(
            "SELECT id FROM registrations WHERE email = %s",
            (email,)
        )
        if cursor.fetchone():
            flash("Email already exists!")
            return redirect("/")

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
                document
            )
        )

        # Retrieve the newly created account ID.
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
            (email,)
        )

        users = cursor.fetchall()

    finally:
        cursor.close()
        connection.close()

    # Verify the submitted password against the stored hash.
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

        # Fetch the existing user BEFORE accessing user fields.
        cursor.execute(
            "SELECT * FROM registrations WHERE id = %s",
            (user_id,)
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
            (email, user_id)
        )
        if cursor.fetchone():
            flash("That email address is already in use.")
            return redirect("/")

        phone = request.form.get("phone", "").strip()
        gender = request.form.get("gender")
        course = request.form.get("course")

        # Preserve the existing hash unless a new plaintext password is provided.
        if (
            new_password
            and new_password != user["password"]
            and not new_password.startswith(("scrypt:", "pbkdf2:", "argon2:"))
        ):
            password = generate_password_hash(new_password)
        else:
            password = user["password"]

        # Keep existing files if no replacement is uploaded.
        photo = save_file(request, "photo") or user["photo"]
        audio = save_file(request, "audio") or user["audio"]
        video = save_file(request, "video") or user["video"]
        document = (
            save_file(request, "document")
            or user["document"]
        )

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
                user_id
            )
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

        cursor.execute(
            "DELETE FROM registrations WHERE id = %s",
            (user_id,)
        )

        session.pop("user_id", None)

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
# SERVE UPLOADED FILES
# =========================

@app.route("/uploads/<filename>")
def uploaded_file(filename):

    return send_from_directory(
        UPLOAD_FOLDER,
        filename
    )


# =========================
# START APPLICATION
# =========================

if __name__ == "__main__":

    init_db()

    debug_mode = (
        os.getenv("FLASK_DEBUG", "0") == "1"
    )

    app.run(
        debug=debug_mode,
        port=5000
    )
