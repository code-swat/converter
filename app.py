import streamlit as st
from config.database import init_db
from config.seed import seed_db

# Initialize database and seed
init_db()
seed_db()

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

def logout():
    st.session_state.logged_in = False
    st.rerun()

login_page = st.Page('pages/login.py', title="Log in", icon=":material/login:")
logout_page = st.Page(logout, title="Log out", icon=":material/logout:")
transformer_page = st.Page('pages/transformer.py', title="Transformer", icon=":material/dashboard:")

if st.session_state.logged_in:
    pg = st.navigation([transformer_page, logout_page])
else:
    pg = st.navigation([login_page])

pg.run()