import sqlite3
import streamlit as st
from sqlalchemy import text

def init_db():
    conn = st.connection('sqlite')
    with conn.session as session:
        session.execute(text('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        '''))
        session.commit() 