import hashlib
import streamlit as st
from sqlalchemy import text

def seed_db():
    conn = st.connection('postgres')
    default_password = "admin#123"
    hashed_default = hashlib.sha256(default_password.encode()).hexdigest()

    with conn.session as session:
        # Check if admin user exists
        result = session.execute(text("SELECT * FROM users WHERE username = 'admin'")).fetchone()
        if not result:
            # Create default admin user
            session.execute(
                text("INSERT INTO users (username, password) VALUES (:username, :password)"),
                {"username": "admin", "password": hashed_default}
            )
            session.commit()
        elif result.password != hashed_default:
            # Update password if it's different from default
            session.execute(
                text("UPDATE users SET password = :password WHERE username = 'admin'"),
                {"password": hashed_default}
            )
            session.commit()