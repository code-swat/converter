import re
import datetime
import streamlit as st
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
            "DEBITOS": float(row["DEBITOS"]) * -1 if row["DEBITOS"] else "", 
            "CREDITOS": float(row["CREDITOS"]) if row["CREDITOS"] else "",
            "SALDO": saldo * -1 if saldo and row["SALDOS"].endswith('-') else saldo
        }

        canonical_rows.append(canonical_row)

    return canonical_rows

class ICBCParser:
    def parse(self, data: List[str]) -> List[Dict[str, str]]:
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

        # Helper function to parse COMPROBANTE, ORIGEN, CANAL
        def parse_comprobante_origen_canal(token: str) -> Tuple[str, str, str]:
            if token == '-':
                return '', '', ''
            parts = token.split()
            if len(parts) >= 3:
                if parts[-1].isalpha():
                    comprobante = ' '.join(parts[:-2])
                    origen = parts[-2]
                    canal = parts[-1]
                else:
                    comprobante = ' '.join(parts[:-1])
                    origen = parts[-1]
                    canal = ''
            elif len(parts) == 2:
                if parts[1].isalpha():
                    comprobante = ''
                    origen = ' '.join(parts)
                    canal = ''
                else:
                    comprobante = parts[0]
                    origen = parts[1]
                    canal = ''
            elif len(parts) == 1:
                comprobante = parts[0]
                origen = ''
                canal = ''
            else:
                comprobante = ''
                origen = ''
                canal = ''
            return comprobante, origen, canal

        # Helper function to parse amount strings to float
        def parse_amount(amount_str: str) -> float:
            if not amount_str:
                return 0.0
            amount_clean = amount_str.replace('.', '').replace(',', '.')
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

        # Process each line
        for text in lines:
            text = text.strip()
            if not text:
                continue  # Skip empty lines

            # Handle initial balance
            if "SALDO ULTIMO EXTRACTO" in text:
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
            if re.match(r'\d{2}-\d{2}', text):
                # Split the line by two or more spaces to separate fields
                tokens = re.split(r'\s{2,}', text)

                # Extract FECHA and the rest from the first token
                first_token = tokens[0]
                fecha_concepto_match = re.match(r'^(\d{2})-(\d{2})\s+(.*)', first_token)
                if fecha_concepto_match:
                    dia, mes, rest = fecha_concepto_match.groups()
                    fecha = f"{dia}/{mes}/{year}"

                    # Check if 'rest' ends with F. VALOR pattern (\d{2}-\d{2})
                    f_valor_match = re.search(r'(\d{2}-\d{2})$', rest)
                    if f_valor_match:
                        concepto = rest[:f_valor_match.start()].strip()
                        f_valor_raw = f_valor_match.group(1)
                        f_valor = f"{f_valor_raw.replace('-', '/')}/{year}"
                    else:
                        concepto = rest.strip()
                        f_valor = ""
                else:
                    # If FECHA is not found, skip this line
                    st.warning(f"Unparsed line (FECHA not found): {text}")
                    continue

                # Initialize fields
                comprobante = ""
                origen = ""
                canal = ""
                debitos = ""
                creditos = ""
                saldos = ""

                # Determine the starting index for COMPROBANTE_ORIGEN_CANAL
                token_idx = 1  # Start from the second token

                # Handle cases where F. VALOR is present
                if f_valor:
                    if token_idx < len(tokens):
                        comp_orig_canal_token = tokens[token_idx]
                        if comp_orig_canal_token == '-':
                            comprobante = ''
                            token_idx += 1
                            if token_idx < len(tokens):
                                origen_token = tokens[token_idx]
                                origen = origen_token
                                canal = ''
                                token_idx += 1
                        else:
                            comp, orig, can = parse_comprobante_origen_canal(comp_orig_canal_token)
                            comprobante = comp
                            origen = orig
                            canal = can
                            token_idx += 1
                else:
                    # Handle cases where F. VALOR is absent
                    if token_idx < len(tokens):
                        comp_orig_canal_token = tokens[token_idx]
                        if comp_orig_canal_token == '-':
                            comprobante = ''
                            token_idx += 1
                            if token_idx < len(tokens):
                                origen_token = tokens[token_idx]
                                origen = origen_token
                                canal = ''
                                token_idx += 1
                        else:
                            comp, orig, can = parse_comprobante_origen_canal(comp_orig_canal_token)
                            comprobante = comp
                            origen = orig
                            canal = can
                            token_idx += 1

                # Collect amount fields from the remaining tokens
                amount_tokens = tokens[token_idx:]

                # Clean and collect amount fields
                amounts = []
                for amt in amount_tokens:
                    amt = amt.strip()
                    if re.match(r'^(\d{1,3}(?:\.\d{3})*|\d+),\d{2}-?$', amt):
                        # Replace thousand separator and decimal comma
                        amt_clean = amt.replace('.', '').replace(',', '.')
                        if amt.endswith('-'):
                            amt_clean = '-' + amt_clean[:-1]  # Negative value
                        try:
                            amount = float(amt_clean)
                            amounts.append(amount)
                        except:
                            amounts.append(0.0)
                    else:
                        # Non-amount tokens are ignored or could be logged
                        pass

                # Assign DEBITOS, CREDITOS, SALDOS based on number of amounts
                if len(amounts) == 1:
                    debitos = amounts[0]
                elif len(amounts) == 2:
                    debitos = amounts[0]
                    saldos = amounts[1]
                elif len(amounts) >= 3:
                    debitos = amounts[0]
                    creditos = amounts[1]
                    saldos = amounts[2]

                # If debitos are greater than 0, then we need to swap them with creditos
                if debitos and debitos > 0:
                    creditos = debitos
                    debitos = 0

                # Calculate expected saldo
                expected_saldo = current_balance
                if debitos:
                    expected_saldo += debitos  # DEBITOS are negative
                if creditos:
                    expected_saldo += creditos

                # Format expected_saldo
                expected_saldo_formatted = format_balance(expected_saldo)

                # Handle SALDOS field
                if len(amounts) >= 2:
                    # If SALDOS is present in data
                    if len(amounts) == 2:
                        saldos_in_data = saldos
                        if saldos_in_data:
                            # Compare with expected_saldo
                            try:
                                saldos_value = float(saldos_in_data.replace('.', '').replace(',', '.').replace('-', ''))
                                if saldos_in_data.endswith('-'):
                                    saldos_value = -saldos_value
                            except:
                                saldos_value = expected_saldo
                            if abs(saldos_value - expected_saldo) > 0.01:
                                st.error(f"SALDOS mismatch on {fecha}: calculated {expected_saldo_formatted}, found {saldos_in_data}")
                        else:
                            # If SALDOS is empty, set it
                            saldos = expected_saldo_formatted
                    elif len(amounts) >= 3:
                        # If SALDOS is present in data
                        if saldos:
                            # Compare with expected_saldo
                            try:
                                saldos_value = float(saldos.replace('.', '').replace(',', '.').replace('-', ''))
                                if saldos.endswith('-'):
                                    saldos_value = -saldos_value
                            except:
                                saldos_value = expected_saldo
                            if abs(saldos_value - expected_saldo) > 0.01:
                                st.error(f"SALDOS mismatch on {fecha}: calculated {expected_saldo_formatted}, found {saldos}")
                        else:
                            # If SALDOS is empty, set it
                            saldos = expected_saldo_formatted

                # Update current_balance
                current_balance = expected_saldo

                # Append the parsed transaction to rows
                rows.append({
                    "FECHA": fecha,
                    "CONCEPTO": concepto,
                    "F. VALOR": f_valor,
                    "COMPROBANTE": comprobante,
                    "ORIGEN": origen,
                    "CANAL": canal,
                    "DEBITOS": f"{debitos:.2f}" if debitos else "",
                    "CREDITOS": f"{creditos:.2f}" if creditos else "",
                    "SALDOS": format_balance(float(saldos)) if saldos else format_balance(current_balance)
                })

        return [convert_to_canonical_format(rows)]

