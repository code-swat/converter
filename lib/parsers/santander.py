import re
import streamlit as st
from typing import Dict, List

def convert_to_canonical_format(data: Dict) -> Dict:
    canonical_rows = []

    for row in data:
        canonical_row = {
            "FECHA": row["Fecha"],
            "DETALLE": row["Movimiento"],
            "REFERENCIA": row["Comprobante"],
            "DEBITOS": float(row["Débito"].replace('.', '').replace(',', '.')) if row["Débito"] else "", 
            "CREDITOS": float(row["Crédito"].replace('.', '').replace(',', '.')) if row["Crédito"] else "",
            "SALDO": float(row["Saldo en cuenta"].replace('.', '').replace(',', '.')) if row["Saldo en cuenta"] else ""
        }

        canonical_rows.append(canonical_row)

    return canonical_rows

class SantanderParser:
    def parse(self, data: List[str]) -> List[List[Dict[str, str]]]:
        data_str = self.clean_pages(data)
        lines = data_str.split('\n')

        transactions = []
        current_date = ''
        current_comprobante = ''
        debito = ''
        credito = ''
        saldo_en_cuenta = ''
        previous_saldo = None
        i = 0
        n = len(lines)
        
        # Find the start index: first date line followed by "Saldo Inicial"
        start_index = -1
        for idx in range(n-1):
            if re.match(r'^\d{2}/\d{2}/\d{2}$', lines[idx].strip()) and 'Saldo Inicial' in lines[idx+1]:
                start_index = idx
                break
        if start_index == -1:
            return []
        i = start_index
        
        while i < n:
            line = lines[i].strip()
            
            # End processing when "Saldo total" is encountered
            if 'Saldo total' in line and 'pesos' in lines[i+1]:
                break
            
            # Check for date and comprobante on the same line
            date_comprobante_match = re.match(r'^(\d{2}/\d{2}/\d{2})\s+(\d+)$', line)
            if date_comprobante_match:
                current_date = date_comprobante_match.group(1)
                current_comprobante = date_comprobante_match.group(2)
                i += 1
                continue
            
            # Check for standalone date line
            date_match = re.match(r'^(\d{2}/\d{2}/\d{2})$', line)
            if date_match:
                current_date = date_match.group(1)
                current_comprobante = ''
                i += 1
                continue
            
            # Check for "Saldo Inicial"
            if 'Saldo Inicial' in line:
                movimiento = 'Saldo Inicial'
                comprobante = ''
                debito = ''
                credito = ''
                # Next line should have 'pesos' and amount
                if i+1 < n and 'pesos' in lines[i+1]:
                    saldo_en_cuenta = self.format_amount(self.parse_amount(lines[i+1]))
                    transactions.append({
                        'Fecha': current_date,
                        'Comprobante': comprobante,
                        'Movimiento': movimiento,
                        'Débito': debito,
                        'Crédito': credito,
                        'Saldo en cuenta': saldo_en_cuenta
                    })
                    previous_saldo = self.parse_amount(lines[i+1])
                    i += 2
                    continue
            
            # Check for comprobante line
            comprobante_match = re.match(r'^(\d{1,15})$', line)
            if comprobante_match and not current_comprobante:
                current_comprobante = comprobante_match.group(1)
                i += 1
                continue
            
            # Collect Movimiento lines
            movimiento_lines = []
            while i < n and not lines[i].strip().startswith('pesos') and not re.match(r'^\d{2}/\d{2}/\d{2}$', lines[i].strip()) and not re.match(r'^\d{1,15}$', lines[i].strip()):
                movimiento_lines.append(lines[i].strip())
                i += 1
            movimiento = '\n'.join(movimiento_lines).strip()
            
            # Collect Débito/Credito and Saldo en cuenta
            debito_credito = ''
            saldo = ''
            if i < n and 'pesos' in lines[i].strip():
                debito_credito = lines[i].strip()
                i += 1
            if i < n and 'pesos' in lines[i].strip():
                saldo = lines[i].strip()
                i += 1
            
            debito_amount = self.parse_amount(debito_credito) if debito_credito else None
            saldo_amount = self.parse_amount(saldo) if saldo else None
            
            if previous_saldo is not None and saldo_amount is not None and debito_amount is not None:
                if abs(previous_saldo - debito_amount - saldo_amount) < 0.01:
                    debito = self.format_amount(debito_amount)
                elif abs(previous_saldo + debito_amount - saldo_amount) < 0.01:
                    credito = self.format_amount(debito_amount)
            saldo_en_cuenta = self.format_amount(saldo_amount) if saldo_amount is not None else ''
            previous_saldo = saldo_amount
            
            transactions.append({
                'Fecha': current_date,
                'Comprobante': current_comprobante,
                'Movimiento': movimiento,
                'Débito': debito,
                'Crédito': credito,
                'Saldo en cuenta': saldo_en_cuenta
            })
            
            # Reset comprobante after use
            current_comprobante = ''
            debito = ''
            credito = ''
        
        return [convert_to_canonical_format(transactions)]

    def parse_amount(self, amount_str):
        amount_str = amount_str.replace(' ', '').replace('pesos', '').replace('menos', '-')
        amount_str = amount_str.replace('.', '').replace(',', '.')
        try:
            return float(amount_str)
        except ValueError:
            return None

    def format_amount(self, amount):
        if amount is None:
            return ''
        return "{:,.2f}".format(amount).replace(',', ' ').replace('.', ',').replace(' ', '.')
    
    def clean_pages(self, pages):
        last_header_regex = r'saldo en cuenta'
        cc_or_ca_regex = r'cuenta corriente n|caja de ahorro n'
        lines = []

        for page in pages:
            first_line = True
            skip_until_headers = False

            for line in page.split('\n'):
                if first_line and re.search(cc_or_ca_regex, line.lower()):
                    skip_until_headers = True
                    continue
                
                if skip_until_headers and re.search(last_header_regex, line.lower()):
                    skip_until_headers = False
                    continue
                
                if not skip_until_headers:
                    lines.append(line)

                first_line = False

        return '\n'.join(line for line in lines if line.strip())
