import hashlib
import streamlit as st
from sqlalchemy import text

def seed_db():
    conn = st.connection('sqlite')
    with conn.session as session:
        # Check if admin user exists
        result = session.execute(text("SELECT * FROM users WHERE username='admin'")).fetchone()
        if not result:
            # Create default admin user
            default_password = "admin"  # You should change this in production
            hashed_password = hashlib.sha256(default_password.encode()).hexdigest()
            session.execute(
                text("INSERT INTO users (username, password) VALUES (:username, :password)"),
                {"username": "admin", "password": hashed_password}
            )
            session.commit() 