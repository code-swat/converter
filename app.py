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

login_page = st.Page('views/login.py', title="Log in", icon=":material/login:")
logout_page = st.Page(logout, title="Log out", icon=":material/logout:")
transformer_page = st.Page('views/transformer.py', title="Transformer", icon=":material/dashboard:")
admin_page = st.Page('views/admin.py', title="Admin", icon=":material/overview:")

if st.session_state.logged_in:
    if st.session_state.username == "admin":
        pg = st.navigation([transformer_page, admin_page, logout_page])
    else:
        pg = st.navigation([transformer_page, logout_page])
else:
    pg = st.navigation([login_page])

pg.run()