import io
from unittest.mock import MagicMock, patch

import pytest
from werkzeug.datastructures import FileStorage


@pytest.fixture
def client():
    import app as app_module

    app_module.app.config["TESTING"] = True
    app_module.app.config["SECRET_KEY"] = "test-secret-key"
    app_module.app.config["WTF_CSRF_ENABLED"] = False

    with app_module.app.test_client() as client:
        with app_module.app.app_context():
            yield client


def test_save_file_no_file():
    from utils import save_file

    mock_request = MagicMock()
    mock_request.files = {}
    assert save_file(mock_request, "photo") is None


def test_save_file_empty_filename():
    from utils import save_file

    mock_request = MagicMock()
    empty_file = FileStorage(stream=io.BytesIO(b""), filename="")
    mock_request.files = {"photo": empty_file}
    assert save_file(mock_request, "photo") is None


def test_save_file_successful_upload():
    from utils import save_file

    mock_request = MagicMock()
    file_storage = FileStorage(
        stream=io.BytesIO(b"dummy image data"),
        filename="test_photo.PNG",
        content_type="image/png",
    )
    mock_request.files = {"photo": file_storage}

    with patch("utils.s3_client.upload_fileobj") as mock_upload:
        key = save_file(mock_request, "photo")
        assert key is not None
        assert key.endswith("_photo.png")
        assert mock_upload.called
        args, kwargs = mock_upload.call_args
        assert kwargs["ExtraArgs"]["ContentType"] == "image/png"


def test_generate_presigned_url():
    from utils import generate_presigned_url

    with patch("utils.s3_client.generate_presigned_url", return_value="https://s3.amazonaws.com/test-url"):
        url = generate_presigned_url("unique_photo.jpg")
        assert url == "https://s3.amazonaws.com/test-url"


def test_generate_presigned_url_with_download():
    from utils import generate_presigned_url

    with patch("utils.s3_client.generate_presigned_url") as mock_presigned:
        mock_presigned.return_value = "https://s3.amazonaws.com/test-url"
        url = generate_presigned_url("abc123_my_doc.pdf", as_attachment=True)
        assert url == "https://s3.amazonaws.com/test-url"
        args, kwargs = mock_presigned.call_args
        params = kwargs["Params"]
        assert "ResponseContentDisposition" in params
        assert 'attachment; filename="my_doc.pdf"' in params["ResponseContentDisposition"]


def test_delete_file_from_s3():
    from utils import delete_file_from_s3

    with patch("utils.s3_client.delete_object") as mock_delete:
        assert delete_file_from_s3("photo.jpg") is True
        mock_delete.assert_called_once_with(
            Bucket="registration-form-files-2026",
            Key="photo.jpg",
        )


def test_delete_files_from_s3():
    from utils import delete_files_from_s3

    with patch("utils.s3_client.delete_object") as mock_delete:
        delete_files_from_s3(["p.jpg", None, "d.pdf"])
        assert mock_delete.call_count == 2


def test_uploaded_file_route_unauthenticated(client):
    response = client.get("/uploads/secret_photo.jpg", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["Location"] in ("/", "http://localhost/")


def test_uploaded_file_route_unauthorized_file(client):
    connection = MagicMock()
    cursor = MagicMock()
    connection.cursor.return_value = cursor

    cursor.fetchone.return_value = {
        "photo": "my_photo.jpg",
        "audio": None,
        "video": None,
        "document": None,
    }

    with client.session_transaction() as session:
        session["user_id"] = 1

    with patch("app.get_db_connection", return_value=connection):
        # Requesting another user's file
        response = client.get("/uploads/other_user_file.jpg", follow_redirects=False)
        assert response.status_code == 302
        assert response.headers["Location"] in ("/", "http://localhost/")


def test_uploaded_file_route_authorized(client):
    connection = MagicMock()
    cursor = MagicMock()
    connection.cursor.return_value = cursor

    cursor.fetchone.return_value = {
        "photo": "my_photo.jpg",
        "audio": None,
        "video": None,
        "document": None,
    }

    with client.session_transaction() as session:
        session["user_id"] = 1

    with patch("app.get_db_connection", return_value=connection), \
         patch("app.generate_presigned_url", return_value="https://s3.presigned.url/test"):
        response = client.get("/uploads/my_photo.jpg", follow_redirects=False)
        assert response.status_code == 302
        assert response.headers["Location"] == "https://s3.presigned.url/test"


def test_account_deletion_deletes_s3_files(client):
    connection = MagicMock()
    cursor = MagicMock()
    connection.cursor.return_value = cursor

    cursor.fetchone.return_value = {
        "photo": "user_photo.jpg",
        "audio": "user_audio.mp3",
        "video": "user_video.mp4",
        "document": "user_doc.pdf",
    }

    with client.session_transaction() as session:
        session["user_id"] = 1

    with patch("app.get_db_connection", return_value=connection), \
         patch("app.delete_files_from_s3") as mock_delete_s3:
        response = client.post("/delete", follow_redirects=False)
        assert response.status_code == 302
        mock_delete_s3.assert_called_once_with(
            ["user_photo.jpg", "user_audio.mp3", "user_video.mp4", "user_doc.pdf"]
        )
