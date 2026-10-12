
from werkzeug.security import (
    generate_password_hash,
    check_password_hash,
)


def test_password_is_hashed():
    password = "Hello@123"

    password_hash = generate_password_hash(password)

    assert password_hash != password


def test_correct_password_is_accepted():
    password = "Hello@123"

    password_hash = generate_password_hash(password)

    assert check_password_hash(password_hash, password)


def test_incorrect_password_is_rejected():
    password_hash = generate_password_hash("Hello@123")

    assert not check_password_hash(
        password_hash,
        "Wrong@123",
    )
