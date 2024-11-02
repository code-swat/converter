import requests
import streamlit as st
from typing import Dict
import time

def recognize_tables(uploaded_file: bytes) -> Dict:
    """Call the DataLab API to recognize tables in the PDF."""
    api_endpoint = "https://www.datalab.to/api/v1/table_rec"
    api_key = st.secrets.datalab.api_key
    
    headers = {
        "X-Api-Key": api_key
    }
    # Read PDF bytes
    files = {
        'file': ('uploaded.pdf', uploaded_file, 'application/pdf')
    }
    
    try:
        response = requests.post(api_endpoint, headers=headers, files=files)
        response.raise_for_status()
        data = response.json()
        check_url = data['request_check_url']
        max_polls = 300
        poll_interval = 2

        for i in range(max_polls):
            time.sleep(poll_interval)

            check_response = requests.get(check_url, headers=headers)
            data = check_response.json()

            if data['status'] == 'complete' and data['pages']:
                tables = [table for page in data['pages'] for table in page['tables']]

                return parse_tables(tables)
            
        st.error("DataLab API request timed out")
        return None
    except requests.exceptions.RequestException as e:
        st.error(f"Error calling DataLab API: {str(e)}")
        return None

def parse_tables(data: Dict) -> Dict:
    rows_data = []

    # Loop through each table
    for table in data:
        rows = table['rows']
        cells = table['cells']

        # Map row_ids to their respective cell texts
        row_dict = {}

        for cell in cells:
            order = cell['order']

            for row_id in cell['row_ids']:
                if row_id not in row_dict:
                    row_dict[row_id] = {}
                for col_id in cell['col_ids']:
                    row_dict[row_id][col_id] = {
                        'text': cell['text'].strip(),
                        'order': order  # Store the order for distinguishing tables
                    }

        # Structure each row as a dictionary and add to rows_data
        for row_id, columns in row_dict.items():
            row = {f"col_{col_id}": columns[col_id]['text'] for col_id in columns}
            row['table_order'] = columns[next(iter(columns))]['order']  # Add the order to the row
            rows_data.append(row)

    return rows_data