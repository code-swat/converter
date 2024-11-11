import streamlit as st
import pandas as pd

from lib.parsers.base import BankParser
from lib.api.file import stats
from lib.data.usage import usage_tracker
from io import BytesIO


if st.session_state.logged_in:
    st.title("PDF Transformer")
    
    selected_bank = st.selectbox(
        "Select a bank",
        BankParser.bank_names()
    )
    
    uploaded_file = st.file_uploader("Upload your PDF", type=['pdf'])

    st.write(f"{selected_bank} status: {BankParser.get_parser_status(selected_bank)}")
    
    if uploaded_file is not None:
        st.write("File uploaded successfully!")
        
        if st.button("Process PDF"):
            with st.spinner("Processing PDF..."):                
                parser = BankParser.get_parser_api(selected_bank)
                bytes_data = uploaded_file.read()
                data = parser(bytes_data)

                if data:
                    # Get the appropriate parser based on selection
                    parser = BankParser.get_parser(selected_bank)
                    # st.write(data)
                    parsed_data = parser.parse(data)
                    
                    if parsed_data:
                        stats = stats(bytes_data)

                        stats['bank'] = selected_bank

                        usage_tracker.record_conversion(stats)
                        st.success("PDF processed successfully!")
                        
                        # Display data in a nice format
                        st.subheader("Processed Data")
                        st.write(parsed_data)
                        
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