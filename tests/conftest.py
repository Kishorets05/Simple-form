    
import pytest
import app as app_module


@pytest.fixture
def client():
    app_module.app.config.update(
        TESTING=True,
        SECRET_KEY="test-secret-key",
    )

    with app_module.app.test_client() as test_client:
        yield test_client
