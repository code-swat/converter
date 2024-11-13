import streamlit as st
from typing import Dict, List
import re

def convert_to_canonical_format(data: Dict) -> Dict:
    canonical_rows = []

    for row in data:
        canonical_row = {
            "FECHA": row["FECHA"],
            "DETALLE": row["MOVIMIENTOS"],
            "REFERENCIA": row["COMPROB."],
            "DEBITOS": row["DEBITOS"].replace('.', ''),
            "CREDITOS": row["CREDITOS"].replace('.', ''),
            "SALDO": row["SALDO"].replace('.', ',').rsplit(',', 1)[0].replace(',', '') + ',' + row["SALDO"].replace('.', ',').rsplit(',', 1)[1]
        }

        canonical_rows.append(canonical_row)

    return canonical_rows

class NacionParser:
    def parse(self, data: List[str]) -> List[List[Dict[str, str]]]:
        # Combine all lines into a single string if data is a list of strings
        text = "\n".join(data)
        
        # Split the text into lines
        lines = text.split("\n")
        
        # Initialize variables
        records = []
        parsing = False
        previous_saldo = None
        
        # Regular expressions
        date_regex = re.compile(r'^\d{2}/\d{2}/\d{2}')
        currency_regex = re.compile(r'\d{1,3}(?:\.\d{3})*,\d{2}-?')
        comprob_regex = re.compile(r'^\d+$')
        
        for line in lines:
            line = line.strip()
            
            # Start parsing when "SALDO ANTERIOR" is found
            if "SALDO ANTERIOR" in line:
                parsing = True
                # Extract the saldo anterior
                saldo_match = re.search(currency_regex, line)
                saldo = saldo_match.group() if saldo_match else "0,00"
                records.append({
                    "FECHA": "",
                    "MOVIMIENTOS": "SALDO ANTERIOR",
                    "COMPROB.": "",
                    "DEBITOS": "",
                    "CREDITOS": "",
                    "SALDO": saldo
                })
                previous_saldo = self._convert_currency(saldo)
                continue
            
            # Stop parsing when "SALDO FINAL" is found
            if "SALDO FINAL" in line:
                parsing = False
                continue
            
            if not parsing:
                continue
            
            # Check if the line starts with a date
            if date_regex.match(line):
                # Split the line into parts
                parts = line.split()
                fecha = parts[0]
                
                # Initialize fields
                movimientos = []
                comprob = ""
                debitos = ""
                creditos = ""
                saldo = ""
                
                # Find the comprob index
                comprob_index = -1
                for i in range(1, len(parts)):
                    if comprob_regex.match(parts[i]):
                        # Check if the next part is currency to confirm COMPROB.
                        if i + 1 < len(parts) and currency_regex.match(parts[i + 1]):
                            comprob = parts[i]
                            movimientos = parts[1:i]
                            comprob_index = i
                            break
                movimientos_str = " ".join(movimientos)
                
                if comprob_index == -1:
                    # If no comprob found, assume entire line after date is movimientos
                    movimientos_str = " ".join(parts[1:])
                else:
                    # After comprob, the next parts are DEBITOS/CREDITOS and SALDO
                    remaining = parts[comprob_index + 1:]
                    currency_matches = currency_regex.findall(" ".join(remaining))
                    
                    if len(currency_matches) >= 2:
                        guessed_value_str = currency_matches[0]
                        saldo_str = currency_matches[1]
                        
                        guessed_value = self._convert_currency(guessed_value_str)
                        current_saldo = self._convert_currency(saldo_str)
                        
                        difference = current_saldo - previous_saldo
                        
                        if difference > 0:
                            creditos = guessed_value_str
                        elif difference < 0:
                            debitos = guessed_value_str
                        # If difference is zero, neither debit nor credit
                        
                        saldo = saldo_str
                        previous_saldo = current_saldo
                    elif len(currency_matches) == 1:
                        # Only saldo present
                        saldo = currency_matches[0]
                        previous_saldo = self._convert_currency(saldo)
                
                record = {
                    "FECHA": fecha,
                    "MOVIMIENTOS": movimientos_str,
                    "COMPROB.": comprob,
                    "DEBITOS": debitos,
                    "CREDITOS": creditos,
                    "SALDO": saldo
                }
                records.append(record)
        
        return [convert_to_canonical_format(records)]
    
    def _convert_currency(self, value: str) -> float:
        """
        Convert a currency string like '55.348,98' or '1.234,56-' to a float 55348.98 or -1234.56
        """
        if not value:
            return 0.0
        negative = False
        if value.endswith('-'):
            negative = True
            value = value[:-1]
        try:
            number = float(value.replace('.', '').replace(',', '.'))
            return -number if negative else number
        except (ValueError, AttributeError):
            return 0.0




expected_output = [
    {
        "FECHA": "",
        "MOVIMIENTOS": "SALDO ANTERIOR",
        "COMPROB.": "",
        "DEBITOS": "",
        "CREDITOS": "",
        "SALDO": "55.348,98"
    },
    {
        "FECHA": "08/05/24",
        "MOVIMIENTOS": "BCA.E.TR.O/BCO -SUC 0001",
        "COMPROB.": "204046",
        "DEBITOS": "",
        "CREDITOS": "400.000,00",
        "SALDO": "455.348,98"
    },
    {
        "FECHA": "28/05/24",
        "MOVIMIENTOS": "DB PM/TOT RESUMEN TCORP",
        "COMPROB.": "1120",
        "DEBITOS": "93.472,38",
        "CREDITOS": "",
        "SALDO": "361.876,60"
    },
    {
        "FECHA": "28/05/24",
        "MOVIMIENTOS": "DB PM/TOT RESUMEN TCORP",
        "COMPROB.": "1120",
        "DEBITOS": "93.472,38",
        "CREDITOS": "",
        "SALDO": "361.876,60"
    }
]