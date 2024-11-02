from typing import Dict

def convert_to_canonical_format(data: Dict) -> Dict:
    canonical_rows = []

    for row in data:
        canonical_row = {
            "FECHA": row["Fecha"],
            "DETALLE": row["Descripción"].split('\n')[0] if row["Descripción"] else "",
            "REFERENCIA": '\n'.join(row["Descripción"].split('\n')[1:]) if row["Descripción"] else "",
            "DEBITOS": row["Débito"], 
            "CREDITOS": row["Crédito"],
            "SALDO": row["Saldo"]
        }

        canonical_rows.append(canonical_row)

    return canonical_rows

class GaliciaParser():
    def parse(self, tables_data: Dict) -> Dict:
        rows = []
        current_row = {}
        description_lines = []

        # Find where the "Movimientos" table starts
        start_processing = False
        
        for entry in tables_data:
            # Check for the headers
            if entry.get('col_0') == "Fecha":
                # If we already have data in the current_row, save it
                if current_row:
                    # Add combined description and append to the list
                    current_row['Descripción'] = '\n'.join(description_lines)
                    rows.append(current_row)
                    current_row = {}
                    description_lines = []
                start_processing = True
                continue

            # Skip entries until we find the start of the movements table
            if not start_processing:
                continue

            # Collect row data
            if 'table_order' in entry:
                if 'col_0' in entry and entry['col_0'] != "Fecha":  # New row starts
                    if current_row and description_lines:  # Save previous row if exists
                        current_row['Descripción'] = '\n'.join(description_lines)
                        rows.append(current_row.copy())
                        current_row = {}
                        description_lines = []
                    
                    if 'col_0' in entry:  # New transaction
                        current_row = {
                            'Fecha': entry.get('col_0', ""),
                            'Origen': entry.get('col_2', ""),
                            'Crédito': entry.get('col_3', ""),
                            'Débito': entry.get('col_4', ""),
                            'Saldo': entry.get('col_5', "")
                        }
                        if 'col_1' in entry:
                            description_lines = [entry['col_1']]
                elif 'col_1' in entry:  # Additional description line
                    description_lines.append(entry['col_1'])

        # Add the last row if exists
        if current_row and description_lines:
            current_row['Descripción'] = '\n'.join(description_lines)
            rows.append(current_row)

        return convert_to_canonical_format(rows)