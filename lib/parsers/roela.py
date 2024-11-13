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
                "SALDO": saldo
            }
        else:
            saldo += importe
            canonical_row = {
                "FECHA": row["Fecha"],
                "DETALLE": row["Descripción"],
                "REFERENCIA": "\n".join([x for x in [row["Comprobante"], row["Concepto"]] if x]),
                "DEBITOS": importe * -1 if importe < 0 else "",
                "CREDITOS": importe if importe > 0 else "",
                "SALDO": saldo
            }

        canonical_rows.append(canonical_row)

    return canonical_rows

def is_saldo_line(line: str) -> bool:
    return line.strip().lower().startswith('saldo al ')

class RoelaParser:
    def parse(self, data: List[str]) -> List[List[Dict[str, str]]]:
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
            
            # Skip "Saldo al" lines and their amount
            if is_saldo_line(line):
                current_index += 2  # Skip both the saldo line and its amount
                continue
                
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
            descripcion = [lines[current_index].strip()]  # Start with first line

            # Check for additional description lines
            while current_index + 1 < len(lines):
                next_line = lines[current_index + 1].strip()
                # If next line is not a date and not a number, it's part of the description
                if not is_date(next_line) and not next_line.isdigit():
                    descripcion.append(next_line)
                    current_index += 1
                else:
                    break

            descripcion = "\n".join(descripcion)  # Join all description lines
            
            # Move to next line to check for Concepto or Fecha
            current_index += 1
            if current_index >= len(lines):
                fecha = ""
                concepto = ""
                comprobante = ""
            else:
                # Initialize variables
                fecha = ""
                concepto = ""
                comprobante = ""
                
                # Check next line
                next_line = lines[current_index].strip()
                current_index += 1
                
                # If it's a date, we're done - no concepto or comprobante
                if is_date(next_line):
                    fecha = next_line
                else:
                    # It must be concepto
                    concepto = next_line
                    
                    # Check for comprobante
                    if current_index < len(lines):
                        next_line = lines[current_index].strip()
                        current_index += 1
                        
                        # If it's a date, we're done - no comprobante
                        if is_date(next_line):
                            fecha = next_line
                        else:
                            # It must be comprobante
                            comprobante = next_line
                            
                            # Finally, check for fecha
                            if current_index < len(lines):
                                next_line = lines[current_index].strip()
                                current_index += 1
                                if is_date(next_line):
                                    fecha = next_line

            # Append the transaction dictionary
            transaction = {
                "Fecha": fecha,
                "Comprobante": comprobante,
                "Concepto": concepto,
                "Descripción": descripcion,
                "Importe": importe
            }
            transactions.append(transaction)

        return [convert_to_canonical_format(transactions)]



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