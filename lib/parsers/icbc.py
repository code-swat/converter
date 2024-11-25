import re
import datetime
from typing import Dict, List, Tuple

def convert_to_canonical_format(data: Dict) -> Dict:
    canonical_rows = []

    for row in data:
        referencia_parts = [row["COMPROBANTE"], row["F. VALOR"], row["ORIGEN"], row["CANAL"]]
        referencia = "\n".join(part for part in referencia_parts if part)
        saldo = float(row["SALDOS"].replace('.', '').replace(',', '.').rstrip('-')) if row["SALDOS"] else ""

        canonical_row = {
            "FECHA": row["FECHA"],
            "DETALLE": row["CONCEPTO"],
            "REFERENCIA": referencia,
            "DEBITOS": float(row["DEBITOS"]) if row["DEBITOS"] else "", 
            "CREDITOS": float(row["CREDITOS"]) if row["CREDITOS"] else "",
            "SALDO": saldo * -1 if saldo and row["SALDOS"].endswith('-') else saldo
        }

        canonical_rows.append(canonical_row)

    return canonical_rows

class ICBCParser:
    def parse(self, data: List[str]) -> List[Dict[str, str]]:
        accounts = []
        rows = []
        current_balance = None
        year = datetime.date.today().year

        # Split the input data into individual lines
        lines = []
        for item in data:
            lines.extend(item.split('\n'))

        # Extract the year from the "PERIODO" line
        for line in lines:
            if "PERIODO" in line:
                periodo_match = re.search(r'PERIODO\s+\d{2}-\d{2}-(\d{4})', line)
                if periodo_match:
                    year = periodo_match.group(1)
                break  # Assuming "PERIODO" appears only once

        # Helper function to parse amount strings to float
        def parse_amount(amount_str: str) -> float:
            if not amount_str:
                return 0.0
            amount_clean = amount_str.replace('.', '').replace(',', '.').replace('-', '')
            try:
                amount = float(amount_clean)
                if amount_str.endswith('-'):
                    amount = -amount
                return amount
            except:
                return 0.0

        # Helper function to format balance back to string
        def format_balance(amount: float) -> str:
            abs_amount = abs(amount)
            # Format with thousands separator '.', decimal separator ','
            formatted = "{:,.2f}".format(abs_amount).replace(',', 'TEMP').replace('.', ',').replace('TEMP', '.')
            if amount < 0:
                formatted += '-'
            return formatted

        # Function to extract amounts from the end of the line
        def extract_amounts_from_end_of_line(line: str) -> Tuple[str, List[str]]:
            amounts = []
            pattern = r'(\d{1,3}(?:\.\d{3})*,\d{2}-?)$'
            while True:
                match = re.search(pattern, line)
                if match:
                    amount_str = match.group(1)
                    amounts.insert(0, amount_str)  # Insert at the beginning
                    line = line[:match.start()].rstrip()
                else:
                    break
            return line, amounts

        # Process each line
        for text in lines:
            text = text.strip()
            if not text:
                continue  # Skip empty lines

            # Handle initial balance
            if "SALDO ULTIMO EXTRACTO" in text:
                if rows:
                    accounts.append(convert_to_canonical_format(rows))
                    rows = []
                # Handle initial balance with proper decimal handling
                match = re.search(r'SALDO ULTIMO EXTRACTO AL (\d{2}/\d{2}/\d{4})\s+([\d\.,-]+)', text)
                if match:
                    saldo_str = match.group(2).replace('.', '').replace(',', '.').rstrip('-')
                    if match.group(2).endswith('-'):
                        saldo_str = '-' + saldo_str
                    try:
                        current_balance = float(saldo_str)
                    except:
                        current_balance = 0.0
                    rows.append({
                        "FECHA": match.group(1),
                        "CONCEPTO": "SALDO ULTIMO EXTRACTO",
                        "F. VALOR": "",
                        "COMPROBANTE": "",
                        "ORIGEN": "",
                        "CANAL": "",
                        "DEBITOS": "",
                        "CREDITOS": "",
                        "SALDOS": format_balance(current_balance)
                    })
                continue

            # Check if line starts with date
            fecha_match = re.match(r'^(\d{2})-(\d{2})\s+(.*)', text)
            if fecha_match:
                dia, mes, rest_of_line = fecha_match.groups()
                fecha = f"{dia}/{mes}/{year}"

                # Extract amounts from the end of the line
                rest_of_line, amount_tokens = extract_amounts_from_end_of_line(rest_of_line)

                # Now, try to extract 'F. VALOR' from 'rest_of_line' if present
                f_valor_match = re.search(r'(\d{2}-\d{2})$', rest_of_line)
                if f_valor_match:
                    f_valor_raw = f_valor_match.group(1)
                    f_valor = f"{f_valor_raw.replace('-', '/')}/{year}"
                    concepto = rest_of_line[:f_valor_match.start()].strip()
                else:
                    f_valor = ''
                    concepto = rest_of_line.strip()

                # Initialize fields
                comprobante = ''
                origen = ''
                canal = ''

                # Now, we can attempt to parse COMPROBANTE, ORIGEN, CANAL if present
                # For simplicity, let's assume they are not present or set them if needed

                # Parse amounts
                amounts = []
                for amt_str in amount_tokens:
                    amt_value = parse_amount(amt_str)
                    amounts.append(amt_value)

                # Assign DEBITOS, CREDITOS, SALDOS based on number of amounts
                debitos = ''
                creditos = ''
                saldos = ''

                if len(amounts) == 1:
                    # Only DEBITOS or CREDITOS (assuming only one amount is present)
                    if amounts[0] < 0:
                        debitos = f"{-amounts[0]:.2f}"
                        current_balance += amounts[0]
                    else:
                        creditos = f"{amounts[0]:.2f}"
                        current_balance += amounts[0]
                    saldos = format_balance(current_balance)
                elif len(amounts) == 2:
                    # DEBITOS/CREDITOS and SALDOS
                    if amounts[0] < 0:
                        debitos = f"{-amounts[0]:.2f}"
                    else:
                        creditos = f"{amounts[0]:.2f}"
                    current_balance = amounts[1]
                    saldos = format_balance(current_balance)
                elif len(amounts) >= 3:
                    # DEBITOS, CREDITOS, SALDOS
                    debitos = f"{-amounts[0]:.2f}" if amounts[0] < 0 else ''
                    creditos = f"{amounts[1]:.2f}" if amounts[1] > 0 else ''
                    current_balance = amounts[2]
                    saldos = format_balance(current_balance)

                # Append the parsed transaction to rows
                rows.append({
                    "FECHA": fecha,
                    "CONCEPTO": concepto,
                    "F. VALOR": f_valor,
                    "COMPROBANTE": comprobante,
                    "ORIGEN": origen,
                    "CANAL": canal,
                    "DEBITOS": debitos,
                    "CREDITOS": creditos,
                    "SALDOS": saldos
                })
            else:
                # If FECHA is not found, skip this line or handle as needed
                continue

        accounts.append(convert_to_canonical_format(rows))

        return accounts
