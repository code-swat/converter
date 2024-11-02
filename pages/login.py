import hashlib
import streamlit as st
from sqlalchemy import text

def verify_password(username, password):
    conn = st.connection('sqlite')
    with conn.session as session:
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        result = session.execute(
            text('SELECT * FROM users WHERE username=:username AND password=:password'), 
            {'username': username, 'password': hashed_password}
        ).fetchone()
        return result is not None

if st.session_state.logged_in == False:
    st.title('Login')

    username = st.text_input('Username')
    password = st.text_input('Password', type='password')
    
    if st.button('Login'):
        if verify_password(username, password):
            st.session_state.logged_in = True
            st.switch_page(st.Page('pages/transformer.py'))
        else:
            st.error('Invalid credentials')