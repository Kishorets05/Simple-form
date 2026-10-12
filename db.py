import os
from urllib.parse import parse_qs, urlparse
import pymysql


def get_db_config():
    """
    Read database connection configuration from environment variables
    with fallback defaults for local development.
    Supports individual environment variables (DB_HOST, DB_USER, etc.),
    connection URIs (MYSQL_URL, DATABASE_URL), and automatic SSL for cloud hosts.
    """
    db_url = os.environ.get("DATABASE_URL") or os.environ.get("MYSQL_URL")

    if db_url:
        if db_url.startswith(("postgres://", "postgresql://")):
            raise ValueError(
                "Render PostgreSQL (postgres://) detected. This application requires MySQL. "
                "Please configure a cloud MySQL provider (e.g. TiDB Serverless, Aiven, or Clever Cloud) "
                "and set DB_HOST, DB_USER, DB_PASSWORD, DB_NAME, or MYSQL_URL."
            )

        if db_url.startswith(("mysql://", "mysql+pymysql://")):
            url = urlparse(db_url)
            query_params = parse_qs(url.query)

            host = url.hostname or "localhost"
            use_ssl = (
                host not in ("localhost", "127.0.0.1")
                or "ssl" in query_params
                or "ssl-mode" in query_params
            )

            config = {
                "host": host,
                "port": int(url.port or 3306),
                "user": url.username or "root",
                "password": url.password or "",
                "database": url.path.lstrip("/").split("?")[0] or "registration_db",
                "cursorclass": pymysql.cursors.DictCursor,
                "autocommit": True,
                "connect_timeout": 10,
            }

            if use_ssl:
                config["ssl"] = {"ssl": True}

            return config

    host = (
        os.environ.get("DB_HOST")
        or os.environ.get("MYSQL_HOST")
        or os.environ.get("MYSQLHOST", "localhost")
    )
    port = int(
        os.environ.get("DB_PORT")
        or os.environ.get("MYSQL_PORT")
        or os.environ.get("MYSQLPORT", 3306)
    )
    user = (
        os.environ.get("DB_USER")
        or os.environ.get("MYSQL_USER")
        or os.environ.get("MYSQLUSER", "root")
    )
    password = (
        os.environ.get("DB_PASSWORD")
        or os.environ.get("MYSQL_PASSWORD")
        or os.environ.get("MYSQLPASSWORD", "root")
    )
    database = (
        os.environ.get("DB_NAME")
        or os.environ.get("MYSQL_DATABASE")
        or os.environ.get("MYSQLDATABASE", "registration_db")
    )

    # Enable SSL automatically for remote cloud databases unless explicitly disabled
    ssl_env = os.environ.get("MYSQL_SSL", "").lower()
    enable_ssl = ssl_env in ("true", "1", "yes") or (
        host not in ("localhost", "127.0.0.1") and ssl_env not in ("false", "0", "no")
    )

    config = {
        "host": host,
        "port": port,
        "user": user,
        "password": password,
        "database": database,
        "cursorclass": pymysql.cursors.DictCursor,
        "autocommit": True,
        "connect_timeout": 10,
    }

    if enable_ssl:
        ssl_dict = {"ssl": True}
        if os.environ.get("MYSQL_SSL_CA"):
            ssl_dict["ca"] = os.environ.get("MYSQL_SSL_CA")
        config["ssl"] = ssl_dict

    return config


# Retained for backward compatibility
DB_CONFIG = get_db_config()


def get_db_connection():
    """Establish and return a MySQL database connection."""
    config = get_db_config()
    return pymysql.connect(**config)


def init_db():
    """
    Initialize database and table schema.
    Supports both local development environments and managed cloud databases.
    """
    try:
        config = get_db_config()
    except Exception as e:
        print(f"Skipping database initialization: {e}")
        return

    db_name = config["database"]

    # In local development, create the database if it does not exist.
    # On managed cloud hosts, databases are pre-created and restricted users
    # may lack CREATE DATABASE privileges.
    try:
        admin_config = {
            k: v for k, v in config.items()
            if k not in ("database", "cursorclass", "autocommit")
        }
        admin_conn = pymysql.connect(**admin_config)
        admin_cursor = admin_conn.cursor()
        admin_cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}`")
        admin_cursor.close()
        admin_conn.close()
    except Exception:
        # Silently skip if database already exists or CREATE DATABASE is restricted
        pass

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS registrations (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                email VARCHAR(100) NOT NULL UNIQUE,
                password VARCHAR(255) NOT NULL,
                phone VARCHAR(20),
                gender VARCHAR(20),
                course VARCHAR(100),
                photo VARCHAR(255),
                audio VARCHAR(255),
                video VARCHAR(255),
                document VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        cursor.close()
        connection.close()
    except Exception as e:
        print(f"Notice: Table initialization deferred or skipped ({e}).")