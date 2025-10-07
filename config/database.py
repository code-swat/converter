import streamlit as st
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
import time

def retry_db_operation(func, max_retries=5, initial_delay=1):
    """
    Retry a database operation with exponential backoff.

    Args:
        func: Function to retry
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds (doubles with each retry)
    """
    for attempt in range(max_retries):
        try:
            return func()
        except OperationalError as e:
            if "SSL connection has been closed" in str(e) or "connection" in str(e).lower():
                if attempt < max_retries - 1:
                    delay = initial_delay * (2 ** attempt)
                    print(f"Database connection error (attempt {attempt + 1}/{max_retries}). Retrying in {delay}s...")
                    time.sleep(delay)
                else:
                    print(f"Failed after {max_retries} attempts")
                    raise
            else:
                # If it's not a connection error, don't retry
                raise

def init_db():
    def _init():
        conn = st.connection('postgres')
        session = conn.session
        session.execute(text('''
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(100) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL
            )
        '''))
        session.commit()
        return True

    retry_db_operation(_init)