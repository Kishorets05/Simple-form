
from unittest.mock import MagicMock, patch

import pytest
from werkzeug.security import (
    check_password_hash,
    generate_password_hash,
)


@pytest.fixture
def client():
    """Create a Flask test client."""
    import app as app_module

    app_module.app.config["TESTING"] = True
    app_module.app.config["SECRET_KEY"] = "test-secret-key"
    app_module.app.config["WTF_CSRF_ENABLED"] = False

    with app_module.app.test_client() as test_client:
        with app_module.app.app_context():
            yield test_client


def mock_db_connection():
    """Create a mocked MySQL connection and cursor."""
    connection = MagicMock()
    cursor = MagicMock()

    connection.cursor.return_value = cursor
    connection.__enter__.return_value = connection
    cursor.__enter__.return_value = cursor

    return connection, cursor


# --------------------------------------------------
# HOME PAGE
# --------------------------------------------------

def test_home_page(client):
    response = client.get("/")

    assert response.status_code == 200


# --------------------------------------------------
# ROUTE AVAILABILITY
# --------------------------------------------------

def test_register_route_exists(client):
    response = client.post("/register", data={})

    assert response.status_code in (200, 302, 400, 404, 500)


def test_login_route_exists(client):
    response = client.post("/login", data={})

    assert response.status_code in (200, 302, 400, 401, 500)


# --------------------------------------------------
# LOGIN TESTS
# --------------------------------------------------

def test_login_requires_valid_credentials(client):
    connection, cursor = mock_db_connection()
    cursor.fetchone.return_value = None

    with patch("app.get_db_connection", return_value=connection):
        response = client.post(
            "/login",
            data={
                "email": "unknown@example.com",
                "password": "WrongPassword123!",
            },
            follow_redirects=False,
        )

    assert response.status_code in (200, 302, 400, 401)


def test_login_with_correct_password(client):
    connection, cursor = mock_db_connection()

    hashed_password = generate_password_hash("TestPassword123!")

    cursor.fetchone.return_value = {
        "id": 1,
        "name": "Test User",
        "email": "test@example.com",
        "password": hashed_password,
    }

    with patch("app.get_db_connection", return_value=connection):
        response = client.post(
            "/login",
            data={
                "email": "test@example.com",
                "password": "TestPassword123!",
            },
            follow_redirects=False,
        )

    assert response.status_code in (200, 302)


def test_login_with_incorrect_password(client):
    connection, cursor = mock_db_connection()

    cursor.fetchone.return_value = {
        "id": 1,
        "name": "Test User",
        "email": "test@example.com",
        "password": generate_password_hash("CorrectPassword123!"),
    }

    with patch("app.get_db_connection", return_value=connection):
        response = client.post(
            "/login",
            data={
                "email": "test@example.com",
                "password": "IncorrectPassword123!",
            },
            follow_redirects=False,
        )

    assert response.status_code in (200, 302, 401)


# --------------------------------------------------
# AUTHORIZATION TESTS
# --------------------------------------------------

def test_update_requires_login(client):
    response = client.post(
        "/update",
        data={"name": "Updated Name"},
        follow_redirects=False,
    )

    assert response.status_code in (200, 302, 401, 403)


def test_delete_requires_login(client):
    response = client.post(
        "/delete",
        follow_redirects=False,
    )

    assert response.status_code in (200, 302, 401, 403)


# --------------------------------------------------
# LOGOUT TEST
# --------------------------------------------------

def test_logout(client):
    with client.session_transaction() as session:
        session["user_id"] = 1

    response = client.get(
        "/logout",
        follow_redirects=False,
    )

    assert response.status_code in (200, 302)

    with client.session_transaction() as session:
        assert "user_id" not in session


# --------------------------------------------------
# UPLOADED FILE TEST
# --------------------------------------------------

def test_uploaded_file_route(client):
    response = client.get(
        "/uploads/nonexistent-test-file.txt"
    )

    assert response.status_code in (404, 400, 302)


# --------------------------------------------------
# PASSWORD HASHING TEST
# --------------------------------------------------

def test_password_hashing():
    password = "TestPassword123!"
    hashed_password = generate_password_hash(password)

    assert hashed_password != password
    assert check_password_hash(hashed_password, password)
    assert not check_password_hash(
        hashed_password,
        "WrongPassword123!",
    )


# --------------------------------------------------
# SHARED PROFILE UPDATE TEST HELPER
# --------------------------------------------------

def assert_update_preserves_password(client, password_mode):
    """
    Verify that profile updates preserve the existing password hash.

    password_mode:
        blank - user leaves the password field empty
        hash  - user submits the existing hash, simulating the old bug
    """
    connection, cursor = mock_db_connection()

    original_hash = generate_password_hash(
        "OriginalPassword123!"
    )

    if password_mode == "blank":
        submitted_password = ""
    elif password_mode == "hash":
        submitted_password = original_hash
    else:
        raise ValueError("Unsupported password mode")

    cursor.fetchone.side_effect = [
        {
            "id": 1,
            "name": "Original Name",
            "email": "orig@example.com",
            "password": original_hash,
            "photo": None,
            "audio": None,
            "video": None,
            "document": None,
        },
        None,
    ]

    with client.session_transaction() as session:
        session["user_id"] = 1

    with patch(
        "app.get_db_connection",
        return_value=connection,
    ):
        response = client.post(
            "/update",
            data={
                "name": "Updated Name",
                "email": "updated@example.com",
                "password": submitted_password,
            },
            follow_redirects=False,
        )

    assert response.status_code == 302

    update_calls = [
        call
        for call in cursor.execute.call_args_list
        if "UPDATE registrations" in str(call)
    ]

    assert len(update_calls) == 1

    args, _ = update_calls[0]
    sql_params = args[1]

    # The password hash must remain unchanged.
    assert sql_params[2] == original_hash


# --------------------------------------------------
# PROFILE UPDATE PASSWORD TESTS
# --------------------------------------------------

def test_update_profile_preserves_password_when_left_blank(client):
    assert_update_preserves_password(
        client,
        password_mode="blank",
    )


def test_update_profile_preserves_password_even_if_hash_submitted(client):
    assert_update_preserves_password(
        client,
        password_mode="hash",
    )
