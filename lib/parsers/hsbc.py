import re
import streamlit as st
from typing import List, Dict

def convert_to_canonical_format(data: Dict) -> Dict:
    canonical_rows = []

    for row in data:
        canonical_row = {
            "FECHA": row["FECHA"],
            "DETALLE": row["REFERENCIA"].lstrip('- '),
            "REFERENCIA": row["NRO"],
            "DEBITOS": float(row["DEBITO"].replace(',', '')) if row["DEBITO"] else "", 
            "CREDITOS": float(row["CREDITO"].replace(',', '')) if row["CREDITO"] else "",
            "SALDO": float(row["SALDO"].replace(',', '').rstrip('-')) * (-1 if row["SALDO"].endswith('-') else 1) if row["SALDO"] else ""
        }

        canonical_rows.append(canonical_row)

    return canonical_rows

class HSBCParser:
    def parse(self, data: List[str]) -> List[Dict[str, str]]:
        #st.write(data)
        records = []
        current_date = ""
        previous_saldo = None
        ignoring = False
        current_year = None

        # Define month mapping
        months = {
            'ENE': '01', 'FEB': '02', 'MAR': '03', 'ABR': '04',
            'MAY': '05', 'JUN': '06', 'JUL': '07', 'AGO': '08',
            'SEP': '09', 'OCT': '10', 'NOV': '11', 'DIC': '12'
        }

        # First pass to extract the year
        for page in data:
            match_year = re.search(r"EXTRACTO DEL \d{2}/\d{2}/(\d{4}) AL", page)
            if match_year:
                current_year = match_year.group(1)
                break

        if not current_year:
            raise ValueError("Year not found in the data.")

        # Split data into lines
        lines = []
        for page in data:
            page_lines = page.split('\n')
            lines.extend(page_lines)

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Ignore lines starting with "HOJA X DE Y"
            if re.match(r'^HOJA\s+\d+\s+DE\s+\d+', line):
                ignoring = True
                continue

            # Ignore content between "C.U.I.T." or "C.U.I.L." and the next header
            if line.startswith(("C.U.I.T.", "C.U.I.L.")):
                ignoring = True
                continue
            if "PRODUCTO" in line and "NRO. CUENTA" in line and "ACUERDO" in line:
                ignoring = True
                continue
            if "FECHA" in line and "SALDO DEUDOR" in line and "NUMERALES" in line:
                ignoring = False
                continue
            if "FECHA" in line and "REFERENCIA" in line and "NRO" in line and "SALDO" in line:
                ignoring = False
                continue
            if ignoring:
                continue

            # Stop processing at "- SALDO FINAL"
            #if line.startswith("- SALDO FINAL"):
            if "- RESUMEN DE ACUERDOS -" in line:
                break

            # Handle "SALDO ANTERIOR"
            if line.startswith("- SALDO ANTERIOR"):
                saldo_match = re.search(r'([\d.,]+-?)$', line)
                if saldo_match:
                    saldo_str = saldo_match.group(1)
                    records.append({
                        "FECHA": "",
                        "REFERENCIA": "SALDO ANTERIOR",
                        "NRO": "",
                        "DEBITO": "",
                        "CREDITO": "",
                        "SALDO": saldo_str
                    })
                    previous_saldo = self.parse_currency(saldo_str)
                continue

            if line.startswith("- SALDO FINAL"):
                continue

            # Handle date lines
            date_match = re.match(r'^(\d{2})-([A-Z]{3})', line)
            if date_match:
                day, month_str = date_match.groups()
                month = months.get(month_str, '00')
                if month == '00':
                    raise ValueError(f"Unknown month abbreviation: {month_str}")
                current_date = f"{day}/{month}/{current_year}"
                line = line[date_match.end():].strip()
            elif not current_date:
                continue  # Skip lines before the first date is found

            # Handle transaction lines starting with "-"
            if line.startswith('-'):
                record = self.parse_transaction_line(line, current_date, previous_saldo)
                if record:
                    records.append(record)
                    saldo_value = self.parse_currency(record['SALDO'])
                    if saldo_value is not None:
                        previous_saldo = saldo_value
                continue

            # Append continuation lines to the previous "REFERENCIA"
            if records:
                records[-1]['REFERENCIA'] += '\n' + line

        return convert_to_canonical_format(records)

    def parse_transaction_line(self, line: str, current_date: str, previous_saldo: float) -> Dict[str, str]:
        record = {
            "FECHA": current_date,
            "REFERENCIA": "",
            "NRO": "",
            "DEBITO": "",
            "CREDITO": "",
            "SALDO": ""
        }

        # Extract SALDO
        saldo_match = re.search(r'([\d.,]+-?)$', line)
        if not saldo_match:
            raise ValueError(f"SALDO not found in line: {line}")
        saldo_str = saldo_match.group(1)
        record['SALDO'] = saldo_str
        line = line[:saldo_match.start()].strip()

        # Extract DEBITO or CREDITO
        amount_match = re.search(r'([\d.,]+-?)$', line)
        if not amount_match:
            raise ValueError(f"Amount (DEBITO/CREDITO) not found in line: {line}")
        amount_str = amount_match.group(1)
        line = line[:amount_match.start()].strip()

        # Extract NRO
        nro_match = re.search(r'(\d+)$', line)
        if nro_match:
            record['NRO'] = nro_match.group(1)
            line = line[:nro_match.start()].strip()

        # The rest is REFERENCIA
        record['REFERENCIA'] = line.strip()

        # Determine DEBITO or CREDITO
        amount = self.parse_currency(amount_str)
        current_saldo = self.parse_currency(saldo_str)

        if previous_saldo is not None and current_saldo is not None and amount is not None:
            # Check for DEBITO
            if abs(previous_saldo - amount - current_saldo) < 0.01:
                record['DEBITO'] = amount_str
            # Check for CREDITO
            elif abs(previous_saldo + amount - current_saldo) < 0.01:
                record['CREDITO'] = amount_str
            else:
                raise ValueError(f"Cannot determine DEBITO/CREDITO for line: {line}")
        else:
            raise ValueError(f"Insufficient data to determine DEBITO/CREDITO for line: {line}")

        return record

    def parse_currency(self, value_str: str) -> float:
        if not value_str:
            return None
        is_negative = False
        value_str = value_str.strip()
        if value_str.endswith('-'):
            is_negative = True
            value_str = value_str[:-1]

        # Remove thousands separators and replace decimal comma with dot
        value_str = value_str.replace(',', '')

        try:
            value = float(value_str)
            if is_negative:
                value = -value
            return value
        except ValueError:
            raise ValueError(f"Invalid currency format: {value_str}")






expected_output = [
    {
        "FECHA": "",
        "REFERENCIA": "SALDO ANTERIOR",
        "NRO": "",
        "DEBITO": "",
        "CREDITO": "",
        "SALDO": "9,813,718.17"
    },
    {
        "FECHA": "02/01/2023",
        "REFERENCIA": "- DEP.CHEQUES AUTOSERV.",
        "NRO": "08567",
        "DEBITO": "",
        "CREDITO": "5,000,000.00",
        "SALDO": "14,813,718.17"
    },
    {
        "FECHA": "02/01/2023",
        "REFERENCIA": "- VALOR NEGOCIADO",
        "NRO": "03295",
        "DEBITO": "",
        "CREDITO": "16,507,043.78",
        "SALDO": "31,320,761.95"
    },
    {
        "FECHA": "02/01/2023",
        "REFERENCIA": "- TRANSF.CAJ.AUTOM C/I\nBCO: CTA:1912200014191 OP:999523 FACOP 105708\nORIGINANTE:30707991115 TROPICAL ARGENTINA SRLL",
        "NRO": "00000",
        "DEBITO": "",
        "CREDITO": "3,354.61",
        "SALDO": "31,324,116.56"
    },
    {
        "FECHA": "02/01/2023",
        "REFERENCIA": "- CHEQUE 48 HORAS",
        "NRO": "66785355",
        "DEBITO": "99,918.00",
        "CREDITO": "",
        "SALDO": "31,224,198.56"
    }
]