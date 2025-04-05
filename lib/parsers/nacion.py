import streamlit as st
from typing import Dict, List
import re

def convert_to_canonical_format(data: List[Dict[str, str]]) -> List[Dict[str, str]]:
    canonical_rows = []
    for row in data:
        # Process SALDO: check for trailing '-' and format accordingly.
        saldo_str = row["SALDO"]
        is_negative = saldo_str.endswith('-')
        if is_negative:
            saldo_str = saldo_str[:-1]  # Remove trailing '-'
        # Replace dots by nothing in the integer part and keep the comma in the fractional part.
        # First, convert to a uniform format with comma as decimal separator.
        saldo_temp = saldo_str.replace('.', ',')
        parts = saldo_temp.rsplit(',', 1)
        if len(parts) == 2:
            formatted_saldo = parts[0].replace(',', '') + ',' + parts[1]
        else:
            formatted_saldo = saldo_temp
        if is_negative:
            formatted_saldo = '-' + formatted_saldo

        canonical_row = {
            "FECHA": row["FECHA"],
            "DETALLE": row["MOVIMIENTOS"],
            "REFERENCIA": row["COMPROB."],
            "DEBITOS": row["DEBITOS"].replace('.', ''),
            "CREDITOS": row["CREDITOS"].replace('.', ''),
            "SALDO": formatted_saldo
        }
        canonical_rows.append(canonical_row)
    return canonical_rows

class NacionParser:
    def parse(self, data: List[str]) -> List[List[Dict[str, str]]]:
        text = "\n".join(data)
        lines = text.split("\n")

        records = []
        previous_saldo = None
        i = 0

        # Find the "SALDO ANTERIOR" header and its following line (the initial balance)
        while i < len(lines):
            line = lines[i].strip()
            if "SALDO ANTERIOR" in line:
                # Extract the saldo value from the end of the line
                parts = line.split()
                saldo_line = parts[-1] if parts else "0,00"
                saldo_line = re.sub(r'A$', '', saldo_line)  # remove trailing A if present
                records.append({
                    "FECHA": "",
                    "MOVIMIENTOS": "SALDO ANTERIOR",
                    "COMPROB.": "",
                    "DEBITOS": "",
                    "CREDITOS": "",
                    "SALDO": saldo_line
                })
                previous_saldo = self._convert_currency(saldo_line)
                i += 1
                break
            i += 1

        # Regex to detect a date at the beginning of a transaction line.
        date_regex = re.compile(r'^\d{2}/\d{2}/\d{2}')

        # Process transactions until "SALDO FINAL" is encountered.
        while i < len(lines):
            line = lines[i].strip()
            if "SALDO FINAL" in line.upper():
                break
            # Only process lines that start with a date.
            if not date_regex.match(line):
                i += 1
                continue

            # Process the entire transaction row which has all fields on one line
            parts = line.split()
            if len(parts) < 4:  # Need at least date, description, comprob, and saldo
                i += 1
                continue

            fecha = parts[0]

            # Find the last numeric value which should be the SALDO
            saldo_str = parts[-1]
            saldo_str = re.sub(r'A$', '', saldo_str)

            # Find COMPROB which is the last integer in the line (ignoring decimals/currency)
            comprob = "0"  # Default value
            for part in reversed(parts[1:-1]):  # Skip date at start and saldo at end
                # Check if it's a pure integer (no commas or periods)
                if part.isdigit():
                    comprob = part
                    break

            # Find the index of COMPROB to extract MOVIMIENTOS properly
            comprob_index = -1
            for j, part in enumerate(parts):
                if part == comprob and j > 0:  # Skip the first element (date)
                    comprob_index = j
                    break

            # Extract MOVIMIENTOS (everything between date and comprob or before saldo)
            if comprob_index > 1:
                movimientos = " ".join(parts[1:comprob_index])
            else:
                # If comprob wasn't found, assume movimientos is everything except date and saldo
                movimientos = " ".join(parts[1:-1])

            # Handle DEBITOS and CREDITOS based on the change in balance
            debitos = ""
            creditos = ""

            # Try to find amount values (with decimal points or commas)
            amount_index = -1
            for j in range(len(parts) - 2, 0, -1):  # Search backward from saldo
                # Look for a value that might be currency (contains a comma or dot)
                if "," in parts[j] or "." in parts[j]:
                    # Skip if this is the COMPROB we already found
                    if j != comprob_index:
                        amount_index = j
                        break

            if amount_index != -1:
                amount_str = parts[amount_index]
                amount_str = re.sub(r'A$', '', amount_str)

                # Determine if this is a debit or credit based on the change in balance
                current_saldo = self._convert_currency(saldo_str)
                if previous_saldo is not None:
                    if current_saldo > previous_saldo:
                        creditos = amount_str
                    elif current_saldo < previous_saldo:
                        debitos = amount_str

            record = {
                "FECHA": fecha,
                "MOVIMIENTOS": movimientos,
                "COMPROB.": comprob,
                "DEBITOS": debitos,
                "CREDITOS": creditos,
                "SALDO": saldo_str
            }
            records.append(record)
            previous_saldo = self._convert_currency(saldo_str)
            i += 1

        return [convert_to_canonical_format(records)]

    def _convert_currency(self, value: str) -> float:
        """
        Convert a currency string like '55.348,98' or '1.234,56-' to a float.
        Also removes a trailing "A" if present.
        """
        if not value:
            return 0.0
        # Remove trailing A if exists.
        value = re.sub(r'A$', '', value)
        negative = False
        if value.endswith('-'):
            negative = True
            value = value[:-1]
        try:
            number = float(value.replace('.', '').replace(',', '.'))
            return -number if negative else number
        except (ValueError, AttributeError):
            return 0.0
