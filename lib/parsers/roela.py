import streamlit as st
from typing import List, Dict
import re

def convert_to_canonical_format(data: Dict) -> Dict:
    canonical_rows = []
    saldo = 0.0
    for i, row in enumerate(data):
        importe = float(row["Importe"])
        
        if i == 0:
            saldo = importe
            canonical_row = {
                "FECHA": row["Fecha"],
                "DETALLE": row["Descripción"],
                "REFERENCIA": "\n".join([x for x in [row["Comprobante"], row["Concepto"]] if x]),
                "DEBITOS": "",
                "CREDITOS": "",
                "SALDO": f"{saldo:,.2f}".replace(',', '@').replace('.', ',').replace('@', '.')
            }
        else:
            saldo += importe
            canonical_row = {
                "FECHA": row["Fecha"],
                "DETALLE": row["Descripción"],
                "REFERENCIA": "\n".join([x for x in [row["Comprobante"], row["Concepto"]] if x]),
                "DEBITOS": f"{importe:.2f}".replace('.', ',') if importe < 0 else "",
                "CREDITOS": f"{importe:.2f}".replace('.', ',') if importe > 0 else "",
                "SALDO": f"{saldo:.2f}".replace('.', ',')
            }

        canonical_rows.append(canonical_row)

    return canonical_rows

class RoelaParser:
    def parse(self, data: List[str]) -> List[Dict[str, str]]:
        # Combine all data strings into a single list of lines
        lines = []
        for block in data:
            lines.extend(block.split('\n'))

        # Initialize list to hold parsed transactions
        transactions = []

        # Regular expression to match dates in dd/mm/yyyy format
        date_pattern = re.compile(r'\d{2}/\d{2}/\d{4}')

        # Helper functions
        def is_importe(line: str) -> bool:
            return line.strip().startswith('$') or line.strip().startswith('-$')

        def is_date(line: str) -> bool:
            return bool(date_pattern.fullmatch(line.strip()))

        # Remove header lines: skip until first importe line
        current_index = 0
        while current_index < len(lines):
            if is_importe(lines[current_index]):
                break
            current_index += 1

        # Parse entries
        while current_index < len(lines):
            line = lines[current_index].strip()
            if not is_importe(line):
                current_index += 1
                continue

            # Parse Importe
            importe = line.replace('$', '').strip()
            if importe.startswith('-'):
                importe = '-' + importe[2:].replace('.', '')
            else:
                importe = importe.replace('.', '')
            importe = importe.replace(',', '.')

            # Move to Descripción
            current_index += 1
            if current_index >= len(lines):
                break
            descripcion = lines[current_index].strip()

            # Move to next line to check for Concepto or Fecha
            current_index += 1
            if current_index >= len(lines):
                fecha = ""
                concepto = ""
                comprobante = ""
            else:
                next_line = lines[current_index].strip()
                if is_date(next_line):
                    # No Concepto and Comprobante
                    concepto = ""
                    comprobante = ""
                    fecha = next_line
                    current_index += 1
                else:
                    # Concepto
                    concepto = next_line
                    # Move to Comprobante
                    current_index += 1
                    if current_index >= len(lines):
                        comprobante = ""
                        fecha = ""
                    else:
                        comprobante = lines[current_index].strip()
                        # Move to Fecha
                        current_index += 1
                        if current_index >= len(lines):
                            fecha = ""
                        else:
                            fecha = lines[current_index].strip()
                            current_index += 1

            # Append the transaction dictionary
            transaction = {
                "Fecha": fecha,
                "Comprobante": comprobante,
                "Concepto": concepto,
                "Descripción": descripcion,
                "Importe": importe
            }
            transactions.append(transaction)

        return convert_to_canonical_format(transactions)



expected_output = [
    {
        "Fecha": "01/08/2023",
        "Comprobante": "",
        "Concepto": "",
        "Descripción": "Saldo Al Inicio",
        "Importe": "314,89"
    },
    {
        "Fecha": "01/08/2023",
        "Comprobante": "00129597",
        "Concepto": "502",
        "Descripción": "RAPIPAGO SIRO",
        "Importe": "4.300,00"
    },
    {
        "Fecha": "01/08/2023",
        "Comprobante": "00135920",
        "Concepto": "502",
        "Descripción": "RAPIPAGO SIRO",
        "Importe": "3.550,00"
    },
    {
        "Fecha": "01/08/2023",
        "Comprobante": "00138846",
        "Concepto": "502",
        "Descripción": "RAPIPAGO SIRO",
        "Importe": "280,00"
    }
]