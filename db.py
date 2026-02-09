from mysql.connector import connect, Error

def get_db_connection():
    return connect(
        host="localhost",
        user="flaskuser",
        password="flaskpass",
        database="securenotes",
        port=3306
    )

def test_connection():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        return result[0]
    except Error as e:
        return str(e)
