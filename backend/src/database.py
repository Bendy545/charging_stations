import mysql.connector
from mysql.connector import Error
from backend.src.config import settings

def get_db_connection():
    """Create and return a database connection"""
    try:
        connection = mysql.connector.connect(**settings.database_config)
        return connection
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        raise Exception("Database connection failed")