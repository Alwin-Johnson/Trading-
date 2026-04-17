"""
Database connection wrapper for PostgreSQL.

Simple, synchronous wrapper with no fancy ORM.
Just raw SQL execution + connection management.
"""

import psycopg
from typing import List, Dict, Any, Optional
from contextlib import contextmanager


class DBConnection:
    """
    PostgreSQL connection wrapper.
    
    Phase-1 guarantees:
    - Simple synchronous operations
    - No ORM, raw SQL only
    - Connection reuse
    - Error handling
    """

    def __init__(self, dsn: str):
        """
        Initialize database connection.
        
        Args:
            dsn: PostgreSQL connection string
                 "postgresql://user:password@host:port/dbname"
                 or "dbname=xxx user=xxx password=xxx host=xxx port=5432"
        """
        self.dsn = dsn
        self.conn = None
        self._connect()

    def _connect(self) -> None:
        """Establish connection to PostgreSQL."""
        try:
            self.conn = psycopg.connect(self.dsn)
            print(f"✅ Database connected")
        except Exception as e:
            raise RuntimeError(f"Failed to connect to database: {e}")

    def fetch_all(self, query: str, params: List[Any] = None) -> List[Dict[str, Any]]:
        """
        Fetch all rows from query result.
        
        Args:
            query: SQL query with %s placeholders
            params: Query parameters
            
        Returns:
            List of dicts (one per row)
        """
        if not self.conn:
            raise RuntimeError("Database connection closed")

        try:
            with self.conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
                cur.execute(query, params or [])
                return cur.fetchall()
        except Exception as e:
            raise RuntimeError(f"Query failed: {e}\nQuery: {query}")

    def fetch_one(self, query: str, params: List[Any] = None) -> Optional[Dict[str, Any]]:
        """
        Fetch single row from query result.
        
        Args:
            query: SQL query with %s placeholders
            params: Query parameters
            
        Returns:
            Dict (one row) or None
        """
        rows = self.fetch_all(query, params)
        return rows[0] if rows else None

    def execute(self, query: str, params: List[Any] = None) -> int:
        """
        Execute query (INSERT/UPDATE/DELETE).
        
        Args:
            query: SQL query with %s placeholders
            params: Query parameters
            
        Returns:
            Number of affected rows
        """
        if not self.conn:
            raise RuntimeError("Database connection closed")

        try:
            with self.conn.cursor() as cur:
                cur.execute(query, params or [])
                self.conn.commit()
                return cur.rowcount
        except Exception as e:
            self.conn.rollback()
            raise RuntimeError(f"Execution failed: {e}\nQuery: {query}")

    def execute_many(self, query: str, params_list: List[List[Any]]) -> int:
        """
        Execute query multiple times with different parameters.
        Useful for batch inserts.
        
        Args:
            query: SQL query with %s placeholders
            params_list: List of parameter lists
            
        Returns:
            Total number of affected rows
        """
        if not self.conn:
            raise RuntimeError("Database connection closed")

        if not params_list:
            return 0

        try:
            with self.conn.cursor() as cur:
                for params in params_list:
                    cur.execute(query, params)
                self.conn.commit()
                return cur.rowcount
        except Exception as e:
            self.conn.rollback()
            raise RuntimeError(f"Batch execution failed: {e}\nQuery: {query}")

    def close(self) -> None:
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
            print("✅ Database disconnected")

    def __enter__(self):
        """Context manager support."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager cleanup."""
        self.close()
