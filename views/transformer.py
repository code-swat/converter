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
        BankParser.bank_names(),
        key="bank_select"
    )

    uploaded_file = st.file_uploader("Upload your PDF", type=['pdf'])

    st.write(f"{selected_bank} status: {BankParser.get_parser_status(selected_bank)}")

    if uploaded_file is not None:
        st.write("File uploaded successfully!")

        if st.button("Process PDF"):
            st.session_state.processed_data = None

            with st.spinner("Processing PDF..."):
                parser = BankParser.get_parser_api(selected_bank)
                bytes_data = uploaded_file.read()
                data = parser(bytes_data)

                if data:
                    parser = BankParser.get_parser(selected_bank)
                    parsed_data = parser.parse(data)
                    #st.write(parsed_data)

                    if parsed_data:
                        file_stats = stats(bytes_data)
                        file_stats['bank'] = selected_bank
                        usage_tracker.record_conversion(file_stats)
                        st.success("PDF processed successfully!")
                        st.session_state.processed_data = parsed_data
                    else:
                        st.error("Error parsing the data")
                        st.session_state.processed_data = None
                else:
                    st.error("Error processing the PDF")
                    st.session_state.processed_data = None

    # Display download buttons if data has been processed
    if 'processed_data' in st.session_state and st.session_state.processed_data:
        file_name = uploaded_file.name.rsplit('.', 1)[0]

        for account_index, account_data in enumerate(st.session_state.processed_data, 1):
            st.subheader(f"Account {account_index}")

            df = pd.DataFrame(account_data)

            excel_buffer = BytesIO()
            df.to_excel(excel_buffer, index=False, engine='openpyxl')
            excel_buffer.seek(0)

            st.download_button(
                label=f"Download Excel file - Account {account_index}",
                data=excel_buffer,
                file_name=f"{file_name}_{account_index}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )