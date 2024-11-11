import hashlib
import streamlit as st
from sqlalchemy import text
import requests
import base64

def verify_password_local(username, password):
    conn = st.connection('sqlite')
    with conn.session as session:
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        result = session.execute(
            text('SELECT * FROM users WHERE username=:username AND password=:password'), 
            {'username': username, 'password': hashed_password}
        ).fetchone()
        return result is not None

def verify_password_api(username, password):
    api_url = "https://api.sigeweb.net/oauth/token"

    try:
        credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
        headers = {
            'Authorization': f'Basic {credentials}'
        }
        response = requests.post(
            api_url,
            headers=headers,
            data={"username": username, "password": password, "grant_type": "password"},
            timeout=5
        )

        return response.status_code == 200
    except requests.exceptions.RequestException:
        st.error("API authentication service is unavailable")
        return False

if st.session_state.logged_in == False:
    st.title('Login')

    with st.form(key='login_form'):
        username = st.text_input('Username')
        password = st.text_input('Password', type='password')
        auth_method = st.radio(
            "Authentication Method",
            ["SIGE", "Local"],
            horizontal=True
        )
        
        if st.form_submit_button('Login'):
            if auth_method == "Local":
                is_valid = verify_password_local(username, password)
            else:
                is_valid = verify_password_api(username, password)
                
            if is_valid:
                st.session_state.logged_in = True
                st.session_state.username = username
                st.switch_page(st.Page('views/transformer.py'))
            else:
                st.error('Invalid credentials')