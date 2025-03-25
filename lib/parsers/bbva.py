import re
import streamlit as st
from typing import List, Dict
from datetime import datetime

def convert_to_canonical_format(data: Dict) -> Dict:
    canonical_rows = []

    for row in data:
        canonical_row = {
            "FECHA": row["FECHA"],
            "DETALLE": row["CONCEPTO"],
            "REFERENCIA": row["ORIGEN"],
            "DEBITOS": float(row["DÉBITO"].lstrip('-').replace('.', '').replace(',', '.')) if row["DÉBITO"] else '',
            "CREDITOS": float(row["CRÉDITO"].replace('.', '').replace(',', '.')) if row["CRÉDITO"] else '',
            "SALDO": float(row["SALDO"].replace('.', '').replace(',', '.')) if row["SALDO"] else ''
        }

        canonical_rows.append(canonical_row)

    return canonical_rows

class BBVAParser:
    # Define date_regex as a class variable
    date_regex = re.compile(r'^(\d{2}/\d{2})(/\d{4})?$')

    def parse(self, data: List[str]) -> List[List[Dict[str, str]]]:
        # Combine all data into a single string
        raw_text = "\n".join(data)

        # Extract year
        year_matches = re.findall(r'Información al: \d{2}/\d{2}/(\d{4})', raw_text)
        if year_matches:
            year = max(int(y) for y in year_matches)
        else:
            year = datetime.now().year

        # Find the initial "Movimientos en cuentas" section
        movimientos_start = re.search(r'Movimientos en cuentas', raw_text, re.IGNORECASE)
        if not movimientos_start:
            return []

        # Start processing from after "Movimientos en cuentas"
        current_pos = movimientos_start.end()
        all_transactions = []

        while True:
            # Find next "SALDO ANTERIOR" section
            saldo_anterior_start = re.search(r'SALDO ANTERIOR', raw_text[current_pos:], re.IGNORECASE)
            if not saldo_anterior_start:
                break

            # Update current position to start of this section
            current_pos += saldo_anterior_start.start()

            # Find next "TOTAL MOVIMIENTOS"
            movimientos_end = re.search(r'TOTAL MOVIMIENTOS', raw_text[current_pos:], re.IGNORECASE)
            if not movimientos_end:
                break

            # Extract the account section
            account_text = raw_text[current_pos:current_pos + movimientos_end.end()]

            # Update position for next iteration
            current_pos += movimientos_end.end()

            # Process this section
            transactions = self.process_account_section(account_text, year)

            # After processing this section, add it to all_transactions
            if transactions:
                all_transactions.append(convert_to_canonical_format(transactions))

        return all_transactions

    def process_account_section(self, account_text: str, year: int) -> List[Dict[str, str]]:
        lines = [line.strip() for line in account_text.split('\n') if line.strip()]

        # Initialize variables for this section
        transactions = []
        current_transaction = {}
        buffer_concept = []
        i = 0  # Initialize counter
        total_lines = len(lines)  # Get total number of lines

        # Handle "SALDO ANTERIOR"
        while i < total_lines:
            if lines[i].lower() == "saldo anterior":
                if i + 1 < total_lines and re.match(r'^\d{1,3}(?:\.\d{3})*,\d{2}$', lines[i + 1]):
                    transactions.append({
                        "FECHA": "",
                        "ORIGEN": "",
                        "CONCEPTO": "SALDO ANTERIOR",
                        "DÉBITO": "",
                        "CRÉDITO": "",
                        "SALDO": lines[i + 1]
                    })
                    i += 2  # Skip SALDO ANTERIOR line and the saldo value line
                else:
                    i += 1
                break
            i += 1

        # Parse all transactions
        while i < total_lines:
            line = lines[i]
            # Now we can use self.date_regex
            date_match = self.date_regex.match(line)
            if date_match:
                # If there's an existing transaction being built, save it
                if current_transaction:
                    # Finalize the previous transaction
                    if buffer_concept:
                        current_transaction['CONCEPTO'] = ' '.join(buffer_concept).strip()
                        buffer_concept = []
                    transactions.append(current_transaction)
                    current_transaction = {}

                # Start a new transaction
                fecha = date_match.group(1)
                if date_match.group(2):
                    # If year is present in the date
                    fecha_full = f"{fecha}/{date_match.group(2)[1:]}"  # Remove the slash before year
                else:
                    # Append the extracted year
                    fecha_full = f"{fecha}/{year}"

                current_transaction['FECHA'] = fecha_full
                current_transaction['ORIGEN'] = ""
                current_transaction['CONCEPTO'] = ""
                current_transaction['DÉBITO'] = ""
                current_transaction['CRÉDITO'] = ""
                current_transaction['SALDO'] = ""

                i += 1
                # Check if next line is ORIGEN or part of CONCEPTO
                if i < total_lines:
                    next_line = lines[i]
                    # ORIGEN is typically a single letter or starts with a letter followed by numbers
                    origen_match = re.match(r'^([A-Z]{1,2}\s?\d*)$', next_line)
                    if origen_match:
                        current_transaction['ORIGEN'] = origen_match.group(1).strip()
                        i += 1
                # Collect CONCEPTO lines until we find DÉBITO/CRÉDITO
                while i < total_lines:
                    concept_line = lines[i]
                    # Check if the line is a currency amount
                    currency_match = re.match(r'^-?\d{1,3}(?:\.\d{3})*,\d{2}$', concept_line)
                    if currency_match:
                        # This line is either DÉBITO or CRÉDITO
                        amount = concept_line
                        if amount.startswith('-'):
                            current_transaction['DÉBITO'] = amount
                        else:
                            current_transaction['CRÉDITO'] = amount
                        i += 1
                        # The next line should be SALDO
                        if i < total_lines:
                            saldo_line = lines[i]
                            saldo_match = re.match(r'^-?\d{1,3}(?:\.\d{3})*,\d{2}$', saldo_line)
                            if saldo_match:
                                current_transaction['SALDO'] = saldo_line
                                i += 1
                        break
                    else:
                        # This line is part of CONCEPTO
                        buffer_concept.append(concept_line)
                        i += 1
                continue
            else:
                # Non-date line outside of transaction, skip
                i += 1

        # After loop ends, append the last transaction if exists
        if current_transaction:
            if buffer_concept:
                current_transaction['CONCEPTO'] = ' '.join(buffer_concept).strip()
            transactions.append(current_transaction)

        # Clean transactions: remove any incomplete transactions
        cleaned_transactions = []
        for tx in transactions:
            if tx['CONCEPTO'] and (tx['SALDO'] or tx['DÉBITO'] or tx['CRÉDITO']):
                cleaned_transactions.append(tx)

        # Add "SALDO AL ..." as the last transaction
        saldo_al_match = re.search(r'SALDO AL .* DE .*', account_text, re.IGNORECASE)
        if saldo_al_match:
            saldo_al_index = saldo_al_match.end()
            saldo_al_lines = [line.strip() for line in account_text[saldo_al_index:].split('\n') if line.strip()]
            if saldo_al_lines:
                cleaned_transactions.append({
                    "FECHA": "",
                    "ORIGEN": "",
                    "CONCEPTO": saldo_al_match.group(0),
                    "DÉBITO": "",
                    "CRÉDITO": "",
                    "SALDO": saldo_al_lines[0]
                })

        return cleaned_transactions
