import streamlit as st
import pandas as pd
import json
from sqlalchemy import text
from datetime import datetime, timedelta
from lib.data.usage import usage_tracker

def get_month_range(selected_date):
    start_date = selected_date.replace(day=1)
    if selected_date.month == 12:
        end_date = selected_date.replace(year=selected_date.year + 1, month=1, day=1) - timedelta(days=1)
    else:
        end_date = selected_date.replace(month=selected_date.month + 1, day=1) - timedelta(days=1)
    return start_date, end_date

if st.session_state.logged_in and st.session_state.username == "admin":
    st.title("Admin Dashboard")

    # Date filter
    current_date = datetime.now()
    selected_month = st.date_input(
        "Select month",
        value=current_date,
        max_value=current_date
    )

    # Get all users
    conn = st.connection('postgres')
    with conn.session as session:
        users = session.execute(text("SELECT username FROM users WHERE username != 'admin'")).fetchall()
        usernames = [user[0] for user in users]

    # User filter
    col1, col2 = st.columns([3, 1])
    with col1:
        selected_user = st.selectbox(
            "Select user",
            ["All Users"] + usernames
        )
    with col2:
        exclude_admin = st.checkbox("Exclude admin user", value=True)

    # Get usage data
    start_date, end_date = get_month_range(selected_month)

    with conn.session as session:
        query = """
            SELECT u.user_name, u.timestamp, u.stats
            FROM usages u
            WHERE u.timestamp BETWEEN :start_date AND :end_date
        """

        if selected_user != "All Users":
            query += " AND u.user_name = :username"
        if exclude_admin:
            query += " AND u.user_name != 'admin'"

        params = {
            'start_date': start_date,
            'end_date': end_date
        }
        if selected_user != "All Users":
            params['username'] = selected_user

        results = session.execute(text(query), params).fetchall()

    if results:
        # Create DataFrame with parsed JSON stats
        df = pd.DataFrame([
            {
                'User': row[0],
                'Timestamp': row[1],
                'Bank': json.loads(row[2]).get('bank', ''),
                'Pages': json.loads(row[2]).get('pages', 0)
            } for row in results
        ])

        # Display metrics
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Total Users", len(df['User'].unique()))
        with col2:
            st.metric("Total Conversions", len(df))
        with col3:
            st.metric("Average Daily Conversions", round(len(df) / (end_date - start_date).days, 2))

        # Display data
        st.subheader("Usage Details")
        st.dataframe(df)

        # Download button
        csv = df.to_csv(index=False)
        st.download_button(
            "Download CSV",
            csv,
            "usage_stats.csv",
            "text/csv",
            key='download-csv'
        )
    else:
        st.info("No usage data found for the selected period")
else:
    st.error("Access denied. Admin privileges required.")