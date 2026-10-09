import os
import time
import pymysql
from werkzeug.security import generate_password_hash, check_password_hash
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    session,
    send_from_directory,
    flash
)

from db import get_db_connection, init_db
from utils import save_file, UPLOAD_FOLDER


app = Flask(__name__)

app.secret_key = 'simple_registration_secret_key'


# HOME PAGE
@app.route('/')
def index():

    user_id = session.get('user_id')

    user = None

    if user_id:

        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute(
            "SELECT * FROM registrations WHERE id = %s",
            (user_id,)
        )

        user = cursor.fetchone()

        cursor.close()
        connection.close()

    return render_template(
        'index.html',
        user=user
    )


# REGISTER
@app.route('/register', methods=['POST'])
def register():

    name = request.form.get('name')
    email = request.form.get('email')

    password = request.form.get('password')
    password = generate_password_hash(password)

    phone = request.form.get('phone')
    gender = request.form.get('gender')
    course = request.form.get('course')

    photo = save_file(request, 'photo')
    audio = save_file(request, 'audio')
    video = save_file(request, 'video')
    document = save_file(request, 'document')

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
                password,
                phone,
                gender,
                course,
                photo,
                audio,
                video,
                document
            )
        )

        user_id = cursor.lastrowid

        session['user_id'] = user_id

        flash('Registration successful!')

    except pymysql.IntegrityError:

        flash('Email already exists!')

    finally:

        cursor.close()
        connection.close()

    return redirect('/')


# LOGIN
@app.route('/login', methods=['POST'])
def login():

    email = request.form.get('email')
    password = request.form.get('password')

    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT *
        FROM registrations
        WHERE email = %s
        """,
        (email,)
    )

    user = cursor.fetchone()

    cursor.close()
    connection.close()

    if user and check_password_hash(user['password'], password):

        session['user_id'] = user['id']

        flash('Login successful!')

    else:

        flash('Invalid email or password!')

    return redirect('/')


# UPDATE
@app.route('/update', methods=['POST'])
def update():

    user_id = session.get('user_id')

    if not user_id:

        flash('Please login first.')

        return redirect('/')

    name = request.form.get('name')
    email = request.form.get('email')
    new_password = request.form.get('password')
    if new_password:
        password = generate_password_hash(new_password)
    else:
        password = user['password']
    phone = request.form.get('phone')
    gender = request.form.get('gender')
    course = request.form.get('course')

    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute(
        "SELECT * FROM registrations WHERE id = %s",
        (user_id,)
    )

    user = cursor.fetchone()

    if not user:

        cursor.close()
        connection.close()

        flash('User not found.')

        return redirect('/')

    photo = user['photo']
    audio = user['audio']
    video = user['video']
    document = user['document']

    new_photo = save_file(request, 'photo')

    if new_photo:
        photo = new_photo

    new_audio = save_file(request, 'audio')

    if new_audio:
        audio = new_audio

    new_video = save_file(request, 'video')

    if new_video:
        video = new_video

    new_document = save_file(request, 'document')

    if new_document:
        document = new_document

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

    connection.commit()

    cursor.close()
    connection.close()

    flash('Profile updated successfully!')

    return redirect('/')


# DELETE
@app.route('/delete', methods=['POST'])
def delete():

    user_id = session.get('user_id')

    if not user_id:

        flash('Please login first.')

        return redirect('/')

    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute(
        "DELETE FROM registrations WHERE id = %s",
        (user_id,)
    )

    connection.commit()

    cursor.close()
    connection.close()

    session.pop('user_id', None)

    flash('Account deleted successfully!')

    return redirect('/')

# LOGOUT
@app.route('/logout')
def logout():

    session.pop('user_id', None)

    flash('Logged out successfully!')

    return redirect('/')

# UPLOADED FILES
@app.route('/uploads/<filename>')
def uploaded_file(filename):

    return send_from_directory(
        UPLOAD_FOLDER,
        filename
    )


# START APPLICATION
if __name__ == '__main__':

    init_db()

    app.run(
        debug=True,
        port=5000
    )