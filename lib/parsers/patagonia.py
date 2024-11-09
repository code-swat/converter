import streamlit as st
from typing import Dict, List

class PatagoniaParser:
    def parse(self, data: List[Dict]) -> List[Dict]:
        # Define the desired output fields
        fields = ["FECHA", "CONCEPTO", "REFER.", "FECHA VALOR", "DEBITOS", "CREDITOS", "SALDO"]
        
        # Sort the data by 'table_order' to ensure proper sequence
        sorted_data = sorted(data, key=lambda x: x.get("table_order", 0))
        
        # Initialize variables to keep track of the current table's state
        headers_mapping = {}
        output = []
        in_table = False  # Flag to indicate if we're inside the target table
        
        for row in sorted_data:
            # Detect header rows by checking if 'col_0' and 'col_1' match expected header titles
            if row.get("col_0") == "FECHA" and row.get("col_1") == "CONCEPTO":
                # Map each column to the corresponding field
                headers_mapping = {}
                if "col_0" in row:
                    headers_mapping["col_0"] = "FECHA"
                if "col_1" in row:
                    headers_mapping["col_1"] = "CONCEPTO"
                if "col_2" in row:
                    headers_mapping["col_2"] = "REFER."
                if "col_3" in row:
                    headers_mapping["col_3"] = "FECHA VALOR"
                if "col_4" in row:
                    headers_mapping["col_4"] = "VALOR"
                if "col_5" in row:
                    headers_mapping["col_5"] = "DEBITOS"
                if "col_6" in row:
                    headers_mapping["col_6"] = "CREDITOS"
                if "col_8" in row:
                    headers_mapping["col_8"] = "SALDO"
                
                in_table = True  # We're now inside the target table
                continue  # Move to the next row

            # Detect page info or other headers to exit the current table context
            if "col_7" in row and "P£gina:" in row["col_7"]:
                in_table = False
                continue  # Skip page info rows
            
            # If a new header row is encountered, reset the table context
            if in_table and row.get("col_0") == "FECHA" and row.get("col_1") == "CONCEPTO":
                # Update headers_mapping for the new table structure
                headers_mapping = {}
                if "col_0" in row:
                    headers_mapping["col_0"] = "FECHA"
                if "col_1" in row:
                    headers_mapping["col_1"] = "CONCEPTO"
                if "col_2" in row:
                    headers_mapping["col_2"] = "REFER."
                if "col_3" in row:
                    headers_mapping["col_3"] = "FECHA VALOR"
                if "col_4" in row:
                    headers_mapping["col_4"] = "VALOR"
                if "col_5" in row:
                    headers_mapping["col_5"] = "DEBITOS"
                if "col_6" in row:
                    headers_mapping["col_6"] = "CREDITOS"
                if "col_8" in row:
                    headers_mapping["col_8"] = "SALDO"
                continue  # Move to the next row
            
            # If we're not inside the target table, skip the row
            if not in_table:
                continue
            
            # Process data rows within the table
            # Initialize a new entry with empty strings for all fields
            entry = {field: "" for field in fields}
            
            # Extract and assign the 'FECHA' field
            entry["FECHA"] = row.get("col_0", "").strip()
            
            # Extract 'CONCEPTO' and optionally concatenate 'col_2' if it exists
            concepto = row.get("col_1", "").strip()
            referencia = row.get("col_2", "").strip()
            if referencia:
                concepto = f"{concepto} {referencia}"
            entry["CONCEPTO"] = concepto
            
            # 'REFER.' is set to empty as per expected output
            entry["REFER."] = ""
            
            # Assign 'FECHA VALOR' if available
            entry["FECHA VALOR"] = row.get("col_3", "").strip()
            
            # Extract 'DEBITOS' from 'col_5'
            entry["DEBITOS"] = row.get("col_5", "").strip()
            
            # Extract 'CREDITOS' from 'col_6' or 'col_7' if 'col_6' is empty
            creditos = row.get("col_6", "").strip()
            if not creditos:
                creditos = row.get("col_7", "").strip()
            entry["CREDITOS"] = creditos
            
            # Extract 'SALDO' from 'col_8'
            entry["SALDO"] = row.get("col_8", "").strip()
            
            # Determine if the row contains meaningful data to include in the output
            # For example, skip rows where 'FECHA' and 'CONCEPTO' are empty
            if any([entry["FECHA"], entry["CONCEPTO"], entry["DEBITOS"], entry["CREDITOS"], entry["SALDO"]]):
                output.append(entry)
        
        # Optionally, display the raw data for debugging purposes
        st.write("Processed Data:", output)
        
        return output

expected_output = [
    {
        "FECHA": "29/12/23",
        "CONCEPTO": "ANTERIOR",
        "REFER.": "",
        "FECHA VALOR": "",
        "DEBITOS": "",
        "CREDITOS": "",
        "SALDO": "215.549,19"
    },
    {
        "FECHA": "2/01/24",
        "CONCEPTO": "DEPOSITO P/CAJA",
        "REFER.": "",
        "FECHA VALOR": "",
        "DEBITOS": "",
        "CREDITOS": "2.000.000,00",
        "SALDO": ""
    },
    {
        "FECHA": "2/01/24",
        "CONCEPTO": "IMP.DB/CR P/CREDITO",
        "REFER.": "",
        "FECHA VALOR": "",
        "DEBITOS": "12.000,00",
        "CREDITOS": "",
        "SALDO": ""
    },
    {
        "FECHA": "2/01/24",
        "CONCEPTO": "COMISION CHEQUES",
        "REFER.": "",
        "FECHA VALOR": "",
        "DEBITOS": "25.347,93",
        "CREDITOS": "",
        "SALDO": ""
    }
]