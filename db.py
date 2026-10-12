import os
from urllib.parse import urlparse
import pymysql


def get_db_config():
    """
    Read database connection configuration from environment variables
    with fallback defaults for local development.
    """
    db_url = os.environ.get("DATABASE_URL") or os.environ.get("MYSQL_URL")
    if db_url and (db_url.startswith("mysql://") or db_url.startswith("mysql+pymysql://")):
        url = urlparse(db_url)
        return {
            "host": url.hostname or "localhost",
            "port": int(url.port or 3306),
            "user": url.username or "root",
            "password": url.password or "",
            "database": url.path.lstrip("/") or "registration_db",
            "cursorclass": pymysql.cursors.DictCursor,
            "autocommit": True,
        }

    return {
        "host": (
            os.environ.get("DB_HOST")
            or os.environ.get("MYSQL_HOST")
            or os.environ.get("MYSQLHOST", "localhost")
        ),
        "port": int(
            os.environ.get("DB_PORT")
            or os.environ.get("MYSQL_PORT")
            or os.environ.get("MYSQLPORT", 3306)
        ),
        "user": (
            os.environ.get("DB_USER")
            or os.environ.get("MYSQL_USER")
            or os.environ.get("MYSQLUSER", "root")
        ),
        "password": (
            os.environ.get("DB_PASSWORD")
            or os.environ.get("MYSQL_PASSWORD")
            or os.environ.get("MYSQLPASSWORD", "root")
        ),
        "database": (
            os.environ.get("DB_NAME")
            or os.environ.get("MYSQL_DATABASE")
            or os.environ.get("MYSQLDATABASE", "registration_db")
        ),
        "cursorclass": pymysql.cursors.DictCursor,
        "autocommit": True,
    }


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
    config = get_db_config()
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