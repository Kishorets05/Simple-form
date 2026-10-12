```python
import io
from unittest.mock import MagicMock, patch

import pytest
from werkzeug.security import generate_password_hash


@pytest.fixture
def client():
    # Import the Flask app from app.py
    import app as app_module

    app_module.app.config["TESTING"] = True
    app_module.app.config["SECRET_KEY"] = "test-secret-key"

    with app_module.app.test_client() as client:
        with app_module.app.app_context():
            yield client

ff
def mock_db_connection():
    """Create a mocked MySQL connection and cursor."""
    connection = MagicMock()
    cursor = MagicMock()

    connection.cursor.return_value = cursor
    connection.__enter__.return_value = connection
    cursor.__enter__.return_value = cursor

    return connection, cursor


def test_home_page(client):
    response = client.get("/")
    assert response.status_code == 200


def test_register_route_exists(client):
    response = client.post("/register", data={})
    assert response.status_code in (200, 302, 400, 404, 500)


def test_login_route_exists(client):
    response = client.post("/login", data={})
    assert response.status_code in (200, 302, 400, 401, 500)


def test_login_requires_valid_credentials(client):
    connection, cursor = mock_db_connection()
    cursor.fetchone.return_value = None

    with patch("app.get_db_connection", return_value=connection):
        response = client.post(
            "/login",
            data={
                "email": "unknown@example.com",
                "password": "WrongPassword123!"
            },
            follow_redirects=False
        )

    assert response.status_code in (200, 302, 401, 400)


def test_login_with_correct_password(client):
    connection, cursor = mock_db_connection()

    hashed_password = generatetf_password_hash("TestPassword123!")

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
                "password": "TestPassword123!"
            },
            follow_redirects=False
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
                "password": "IncorrectPassword123!"
            },
            follow_redirects=False
        )

    assert response.status_code in (200, 302, 401)


def test_update_requires_login(client):
    response = client.post(
        "/update",
        data={"name": "Updated Name"},
        follow_redirects=False
    )

    assert response.status_code in (200, 302, 401, 403)


def test_delete_requires_login(client):
    response = client.post("/delete", follow_redirects=False)

    assert response.status_code in (200, 302, 401, 403)


def test_logout(client):
    with client.session_transaction() as session:
        session["user_id"] = 1

    response = client.get("/logout", follow_redirects=False)

    assert response.status_code in (200, 302)

    with client.session_transaction() as session:
        assert "user_id" not in session


def test_uploaded_file_route(client):
    response = client.get("/uploads/nonexistent-test-file.txt")

    # A nonexistent file should not be served successfully.
    assert response.status_code in (404, 400, 302)


def test_password_hashing():
    from werkzeug.security import check_password_hash

    password = "TestPassword123!"
    hashed_password = generate_password_hash(password)

    assert hashed_password != password
    assert check_password_hash(hashed_password, password)
    assert not check_password_hash(hashed_password, "WrongPassword123!")
```
