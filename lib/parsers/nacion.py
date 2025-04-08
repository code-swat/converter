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
            if line.upper() == "SALDO ANTERIOR":
                i += 1  # The next line should contain the amount.
                saldo_line = lines[i].strip() if i < len(lines) else "0,00"
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

            # Line with date and initial part of MOVIMIENTOS.
            parts = line.split()
            fecha = parts[0]
            movimientos = " ".join(parts[1:])
            i += 1

            # If the next line is not an integer, then it is a continuation of MOVIMIENTOS.
            if i < len(lines) and not lines[i].strip().isdigit():
                movimientos += " " + lines[i].strip()
                i += 1

            # Next line must be COMPROB. (always an integer).
            if i >= len(lines):
                break
            comprob_line = lines[i].strip()
            if not comprob_line.isdigit():
                i += 1
                continue
            comprob = comprob_line
            i += 1

            # Next line: transaction amount.
            if i >= len(lines):
                break
            guessed_value_str = lines[i].strip()
            # Remove trailing "A" if present.
            guessed_value_str = re.sub(r'A$', '', guessed_value_str)
            i += 1

            # Next line: SALDO after the transaction.
            if i >= len(lines):
                break
            saldo_str = lines[i].strip()
            saldo_str = re.sub(r'A$', '', saldo_str)
            i += 1

            # Determine if this amount is a debit or a credit based on the change in balance.
            guessed_value = self._convert_currency(guessed_value_str)
            current_saldo = self._convert_currency(saldo_str)
            difference = current_saldo - previous_saldo
            debitos = ""
            creditos = ""
            if difference > 0:
                creditos = guessed_value_str
            elif difference < 0:
                debitos = guessed_value_str

            record = {
                "FECHA": fecha,
                "MOVIMIENTOS": movimientos,
                "COMPROB.": comprob,
                "DEBITOS": debitos,
                "CREDITOS": creditos,
                "SALDO": saldo_str
            }
            records.append(record)
            previous_saldo = current_saldo

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
