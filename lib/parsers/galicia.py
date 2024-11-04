import re
from typing import Dict, List

def convert_to_canonical_format(data: Dict) -> Dict:
    canonical_rows = []

    for row in data:
        canonical_row = {
            "FECHA": row["Fecha"],
            "DETALLE": row["Descripción"].split('\n')[0] if row["Descripción"] else "",
            "REFERENCIA": '\n'.join(row["Descripción"].split('\n')[1:]) if row["Descripción"] else "",
            "DEBITOS": row["Débito"].replace('.', ''), 
            "CREDITOS": row["Crédito"].replace('.', ''),
            "SALDO": row["Saldo"].replace('.', ',')
        }

        canonical_rows.append(canonical_row)

    return canonical_rows

class GaliciaParser:
    def parse(self, data: List[str]) -> List[Dict[str, str]]:
        """
        Parses the provided bank statement data and extracts transaction details.

        Args:
            data (List[str]): List of strings containing the bank statement data.

        Returns:
            List[Dict[str, str]]: A list of dictionaries, each representing a transaction.
        """
        
        # Concatenate all data into a single string and split into lines
        full_text = "\n".join(data)
        lines = full_text.split("\n")
        
        # Define regex patterns
        date_pattern = re.compile(r"^\d{2}/\d{2}/\d{2}$")
        # Updated currency pattern to allow optional trailing '-'
        currency_pattern = re.compile(r"-?\d{1,3}(?:\.\d{3})*,\d{2}-?$")
        stop_phrase = "Consolidado de retención de impuestos"
        
        transactions = []
        in_movimientos = False
        i = 0
        total_lines = len(lines)
        
        while i < total_lines:
            line = lines[i].strip()
            
            # Check for the start of "Movimientos"
            if not in_movimientos:
                if "Movimientos" in line:
                    in_movimientos = True
                i += 1
                continue
            
            # Check for the end of the transactions section
            if stop_phrase in line:
                break
            
            # Check if the line is a date
            if date_pattern.match(line):
                transaction = {
                    'Fecha': line,
                    'Descripción': '',
                    'Origen': '',
                    'Crédito': '',
                    'Débito': '',
                    'Saldo': ''
                }
                i += 1
                description_lines = []
                
                # Collect description lines
                while i < total_lines:
                    desc_line = lines[i].strip()
                    # Stop if line matches currency, date, or is empty
                    if currency_pattern.match(desc_line) or date_pattern.match(desc_line) or desc_line == '':
                        break
                    description_lines.append(desc_line)
                    i += 1
                
                # Assign description with newline separators
                transaction['Descripción'] = "\n".join(description_lines)
                
                # Optionally capture 'Origen' if present
                if i < total_lines:
                    next_line = lines[i].strip()
                    if not currency_pattern.match(next_line) and not date_pattern.match(next_line) and next_line != '':
                        transaction['Origen'] = next_line
                        i += 1
                
                # Capture Crédito or Débito
                if i < total_lines:
                    credit_debit_line = lines[i].strip()
                    credit_debit_match = currency_pattern.match(credit_debit_line)
                    if credit_debit_match:
                        if credit_debit_line.startswith('-'):
                            transaction['Débito'] = credit_debit_line
                        else:
                            transaction['Crédito'] = credit_debit_line
                        i += 1
                    else:
                        raise ValueError(f"Unexpected format for Crédito/Débito at line {i}: '{credit_debit_line}'.")
                        i += 1  # Increment to avoid infinite loop
                
                # Capture Saldo
                if i < total_lines:
                    saldo_line = lines[i].strip()
                    saldo_match = currency_pattern.match(saldo_line)
                    if saldo_match:
                        # Handle Saldo with trailing '-'
                        if saldo_line.endswith('-'):
                            # Remove the trailing '-', replace thousand separators, and prepend '-'
                            saldo = '-' + saldo_line[:-1].replace('.', '').replace(',', '.')
                        else:
                            saldo = saldo_line.replace('.', '').replace(',', '.')
                        transaction['Saldo'] = saldo
                        i += 1
                    else:
                        raise ValueError(f"Unexpected format for Saldo at line {i}: '{saldo_line}'.")
                        i += 1  # Increment to avoid infinite loop
                
                transactions.append(transaction)
            else:
                # If the line doesn't match a date, skip it
                i += 1
        
        return convert_to_canonical_format(transactions)
