import mysql.connector
from mysql.connector import pooling, Error
from backend.src.core.config import settings
import logging

logger = logging.getLogger(__name__)

_connection_pool = None

def get_connection_pool():
    global _connection_pool
    if _connection_pool is None:
        try:
            _connection_pool = pooling.MySQLConnectionPool(
                pool_name="charging_station_pool",
                pool_size=5,
                **settings.database_config
            )
            logger.info("Database connection pool created")
        except Error as e:
            logger.error(f"Failed to create connection pool: {e}")
            raise
    return _connection_pool

def get_db_connection():
    """Get a connection from the pool"""
    try:
        pool = get_connection_pool()
        return pool.get_connection()
    except Error as e:
        logger.error(f"Failed to get connection: {e}")
        return mysql.connector.connect(**settings.database_config)