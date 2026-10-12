
import app as app_module


def test_flask_application_exists():
    assert app_module.app is not None


def test_register_route_exists():
    rules = {
        (rule.rule, method)
        for rule in app_module.app.url_map.iter_rules()
        for method in rule.methods
    }

    assert ("/register", "POST") in rules


def test_login_route_exists():
    rules = {
        (rule.rule, method)
        for rule in app_module.app.url_map.iter_rules()
        for method in rule.methods
    }

    assert ("/login", "POST") in rules
