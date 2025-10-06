import streamlit as st
from sqlalchemy import text

def init_db():
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