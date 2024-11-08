import streamlit as st
from typing import Dict
from lib.parsers.base import BankParser
import pandas as pd
from io import BytesIO


if st.session_state.logged_in:
    st.title("PDF Transformer")
    
    selected_bank = st.selectbox(
        "Select a bank",
        BankParser.bank_names()
    )
    
    uploaded_file = st.file_uploader("Upload your PDF", type=['pdf'])
    
    if uploaded_file is not None:
        st.write("File uploaded successfully!")
        
        if st.button("Process PDF"):
            with st.spinner("Processing PDF..."):                
                recognize_tables = BankParser.get_parser_api(selected_bank)
                tables_data = recognize_tables(uploaded_file)

                if tables_data:
                    # Get the appropriate parser based on selection
                    parser = BankParser.get_parser(selected_bank)
                    parsed_data = parser.parse(tables_data)
                    
                    if parsed_data:
                        st.success("PDF processed successfully!")
                        
                        # Display data in a nice format
                        #st.subheader("Processed Data")
                        #st.write(parsed_data)
                        
                        # Convert to DataFrame and Excel
                        df = pd.DataFrame(parsed_data)
                        
                        # Create Excel file in memory
                        excel_buffer = BytesIO()
                        df.to_excel(excel_buffer, index=False, engine='openpyxl')
                        excel_buffer.seek(0)
                        
                        # Download button
                        st.download_button(
                            label="Download Excel file",
                            data=excel_buffer,
                            file_name=f"{selected_bank}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                    else:
                        st.error("Error parsing the data")
