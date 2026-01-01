from typing import Optional, Any
import mysql.connector
from mysql.connector import Error
from backend.src.core.config import settings
import logging

logger = logging.getLogger(__name__)

class BaseRepository:
    """
    Base repository with common database operations.
    Implements context manager for automatic connection management.
    """

    def __init__(self, connection=None):
        """
        Initialize repository.

        Args:
            connection: Optional existing database connection.
                       If None, repository will create its own connection.
        """
        self._connection = connection
        self._cursor = None
        self._owns_connection = connection is None

    def __enter__(self):
        """Context manager entry - creates connection and cursor"""
        if self._owns_connection:
            try:
                self._connection = mysql.connector.connect(**settings.database_config)
            except Error as e:
                logger.error(f"Failed to connect to database: {e}")
                raise

        self._cursor = self._connection.cursor(dictionary=True)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - closes cursor and connection"""
        if self._cursor:
            self._cursor.close()
            self._cursor = None

        if self._owns_connection and self._connection:
            if exc_type:
                # Exception occurred - rollback
                self._connection.rollback()
                logger.warning(f"Transaction rolled back due to {exc_type.__name__}")
            else:
                # Success - commit
                self._connection.commit()

            self._connection.close()
            self._connection = None

        # Don't suppress exceptions
        return False

    @property
    def cursor(self):
        """Get the current database cursor"""
        if self._cursor is None:
            raise RuntimeError("Repository not initialized. Use 'with' statement.")
        return self._cursor

    @property
    def connection(self):
        """Get the current database connection"""
        if self._connection is None:
            raise RuntimeError("Repository not initialized. Use 'with' statement.")
        return self._connection

    def commit(self):
        """Manually commit the current transaction"""
        if self._connection:
            self._connection.commit()
            logger.debug("Transaction committed")

    def rollback(self):
        """Manually rollback the current transaction"""
        if self._connection:
            self._connection.rollback()
            logger.warning("Transaction rolled back")

    def execute(self, query: str, params: tuple = None) -> int:
        """
        Execute a query and return rows affected.

        Args:
            query: SQL query string
            params: Query parameters

        Returns:
            Number of rows affected
        """
        try:
            if params:
                self.cursor.execute(query, params)
            else:
                self.cursor.execute(query)
            return self.cursor.rowcount
        except Error as e:
            logger.error(f"Query execution failed: {e}")
            logger.error(f"Query: {query}")
            logger.error(f"Params: {params}")
            raise

    def fetchone(self, query: str, params: tuple = None) -> Optional[dict]:
        """
        Execute query and fetch one row.

        Args:
            query: SQL query string
            params: Query parameters

        Returns:
            Single row as dictionary or None
        """
        self.execute(query, params)
        return self.cursor.fetchone()

    def fetchall(self, query: str, params: tuple = None) -> list[dict]:
        """
        Execute query and fetch all rows.

        Args:
            query: SQL query string
            params: Query parameters

        Returns:
            List of rows as dictionaries
        """
        self.execute(query, params)
        return self.cursor.fetchall()

    def insert(self, query: str, params: tuple) -> int:
        """
        Execute INSERT query and return last inserted ID.

        Args:
            query: SQL INSERT query
            params: Insert parameters

        Returns:
            Last inserted row ID
        """
        self.execute(query, params)
        return self.cursor.lastrowid

    def bulk_insert(self, query: str, data: list[tuple]) -> int:
        """
        Execute bulk INSERT.

        Args:
            query: SQL INSERT query
            data: List of tuples with insert data

        Returns:
            Number of rows inserted
        """
        if not data:
            return 0

        try:
            self.cursor.executemany(query, data)
            return self.cursor.rowcount
        except Error as e:
            logger.error(f"Bulk insert failed: {e}")
            raise

    def table_exists(self, table_name: str) -> bool:
        """Check if a table exists in the database"""
        query = """
            SELECT COUNT(*) as count
            FROM information_schema.tables 
            WHERE table_schema = DATABASE() 
            AND table_name = %s
        """
        result = self.fetchone(query, (table_name,))
        return result['count'] > 0 if result else False