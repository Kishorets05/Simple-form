import pymysql


DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'root',
    'database': 'registration_db',
    'cursorclass': pymysql.cursors.DictCursor,
    'autocommit': True
}


def get_db_connection():
    return pymysql.connect(**DB_CONFIG)


def init_db():

    connection = pymysql.connect(
        host='localhost',
        user='root',
        password='root'
    )

    cursor = connection.cursor()

    cursor.execute(
        "CREATE DATABASE IF NOT EXISTS registration_db"
    )

    cursor.close()
    connection.close()


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