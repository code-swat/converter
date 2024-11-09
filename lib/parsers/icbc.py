import re
import streamlit as st
from typing import Dict, List, Tuple

class ICBCParser:
    def parse(self, data: List[str]) -> Dict:
        st.write("ICBC PARSER")
        st.write(data)
        rows = []
        year = "2024"  # Default year

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
                comprobante = ' '.join(parts[:-2])
                origen = parts[-2]
                canal = parts[-1]
            elif len(parts) == 2:
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
                    rows.append({
                        "FECHA": match.group(1),
                        "CONCEPTO": "SALDO ULTIMO EXTRACTO",
                        "E. VALOR": "",
                        "COMPROBANTE": "",
                        "ORIGEN": "",
                        "CANAL": "",
                        "DEBITOS": "",
                        "CREDITOS": "",
                        "SALDOS": match.group(2).replace('.', '').replace(',', '.')
                    })
                continue

            # Handle regular transactions
            if re.match(r'\d{2}-\d{2}', text):
                # Split the line by two or more spaces to separate fields
                tokens = re.split(r'\s{2,}', text)

                # Extract FECHA and the rest from the first token
                first_token = tokens[0]
                fecha_concepto_match = re.match(r'^(\d{2})-(\d{2})\s+(.*)', first_token)
                if fecha_concepto_match:
                    dia, mes, rest = fecha_concepto_match.groups()
                    fecha = f"{dia}/{mes}/{year}"

                    # Check if 'rest' ends with E. VALOR pattern (\d{2}-\d{2})
                    e_valor_match = re.search(r'(\d{2}-\d{2})$', rest)
                    if e_valor_match:
                        concepto = rest[:e_valor_match.start()].strip()
                        e_valor_raw = e_valor_match.group(1)
                        e_valor = f"{e_valor_raw.replace('-', '/')}/{year}"
                    else:
                        concepto = rest.strip()
                        e_valor = ""
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

                # Handle cases where E. VALOR is present
                if e_valor:
                    if token_idx < len(tokens):
                        comp_orig_canal_token = tokens[token_idx]
                        if comp_orig_canal_token == '-':
                            comprobante = ''
                            token_idx += 1
                            if token_idx < len(tokens):
                                origen_token = tokens[token_idx]
                                origen, canal = origen_token.split(' ', 1) if ' ' in origen_token else (origen_token, '')
                                token_idx += 1
                        else:
                            comp, orig, can = parse_comprobante_origen_canal(comp_orig_canal_token)
                            comprobante = comp
                            origen = orig
                            canal = can
                            token_idx += 1
                else:
                    # Handle cases where E. VALOR is absent
                    if token_idx < len(tokens):
                        comp_orig_canal_token = tokens[token_idx]
                        if comp_orig_canal_token == '-':
                            comprobante = ''
                            token_idx += 1
                            if token_idx < len(tokens):
                                origen_token = tokens[token_idx]
                                origen, canal = origen_token.split(' ', 1) if ' ' in origen_token else (origen_token, '')
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
                    if re.match(r'^-?[\d\.,]+-?$', amt):
                        # Replace thousand separator and decimal comma
                        amt_clean = amt.replace('.', '').replace(',', '.') if '-' not in amt else amt.replace('.', '').replace(',', '.').replace('-', '')
                        if amt.endswith('-'):
                            amt_clean += '-'
                        amounts.append(amt_clean)
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
                # If more than 3 amounts, you can extend the logic as needed

                # Append the parsed transaction to rows
                rows.append({
                    "FECHA": fecha,
                    "CONCEPTO": concepto,
                    "E. VALOR": e_valor,
                    "COMPROBANTE": comprobante,
                    "ORIGEN": origen,
                    "CANAL": canal,
                    "DEBITOS": debitos,
                    "CREDITOS": creditos,
                    "SALDOS": saldos
                })

        return {
            "bank": "ICBC",
            "tables": rows
        }