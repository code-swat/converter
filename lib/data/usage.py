import streamlit as st
import json
from typing import Dict, Optional
from sqlalchemy import text

class UsageTracker:
    def __init__(self):
        # Ensure the table exists
        self._create_table_if_not_exists()

    def _create_table_if_not_exists(self):
        """Create the usages table if it doesn't exist"""
        conn = st.connection('postgres')

        try:
            with conn.session as session:
                session.execute(text("""
                    CREATE TABLE IF NOT EXISTS usages (
                        id SERIAL PRIMARY KEY,
                        user_name TEXT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        stats TEXT
                    )
                """))
                session.commit()
        except Exception as e:
            raise e

    def record_conversion(self, stats: Dict) -> None:
        """
        Record a conversion event for the current user in the database
        """
        username = st.session_state.get('username', 'anonymous')
        conn = st.connection('postgres')
        
        try:
            with conn.session as session:
                session.execute(
                    text("""
                    INSERT INTO usages (user_name, stats, timestamp)
                    VALUES (:user, :stats, CURRENT_TIMESTAMP)
                    """),
                    {'user': username, 'stats': json.dumps(stats)}
                )
                session.commit()
        except Exception as e:
            raise e

    def get_user_stats(self, username: Optional[str] = None) -> Dict:
        """
        Get usage statistics for a specific user or current user from database
        """
        username = username or st.session_state.get('username', 'anonymous')
        conn = st.connection('postgres')

        with conn.session as session:
            result = session.execute(text("""
                SELECT timestamp, stats
                FROM usages
                WHERE user_name = :username
                ORDER BY timestamp DESC
            """),
            {'username': username}
            )
            
            records = result.fetchall()
            
            if not records:
                return {
                    'username': username,
                    'total_conversions': 0,
                    'total_tokens': 0,
                    'total_characters': 0,
                    'conversion_history': []
                }
            
            conversion_history = [{
                'timestamp': record[0],
                'stats': json.loads(record[1])
            } for record in records]
            
            total_conversions = len(records)
            total_tokens = sum(record['stats'].get('total_tokens', 0) for record in conversion_history)
            total_characters = sum(record['stats'].get('total_characters', 0) for record in conversion_history)
            
            return {
                'username': username,
                'total_conversions': total_conversions,
                'total_tokens': total_tokens,
                'total_characters': total_characters,
                'conversion_history': conversion_history
            }

# Create a global instance of the usage tracker
usage_tracker = UsageTracker()
