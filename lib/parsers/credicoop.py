import re
from typing import Dict, List

def convert_to_canonical_format(data: Dict) -> Dict:
    canonical_rows = []

    for row in data:
        canonical_row = {
            "FECHA": row["FECHA"],
            "DETALLE": row["DESCRIPCION"].split('\n')[0] if row["DESCRIPCION"] else "",
            "REFERENCIA": '\n'.join(row["DESCRIPCION"].split('\n')[1:]) if row["DESCRIPCION"] else "",
            "DEBITOS": row["DEBITO"], 
            "CREDITOS": row["CREDITO"],
            "SALDO": row["SALDO"]
        }

        canonical_rows.append(canonical_row)

    return canonical_rows

class CredicoopParser:
    def parse(self, data: List[str]) -> Dict:
        # Combine all pages into a single list of lines
        lines = []
        for page in data:
            lines.extend(page.split('\n'))

        rows = []
        current_row = None
        parsing_transactions = False

        # Regular expressions
        date_regex = re.compile(r'^\s*(\d{2}/\d{2}/\d{2})\s+')
        amount_regex = re.compile(
            r'([-−]?[\d\.,]+)'                # First amount (DEBITO or CREDITO)
            r'(?:\s+([-−]?[\d\.,]+))?'        # Optional second amount (CREDITO or SALDO)
            r'(?:\s+([-−]?[\d\.,]+))?'        # Optional third amount (SALDO)
            r'\s*$'
        )

        # Keywords that indicate non-transactional lines
        footer_keywords = [
            'CONTINUA EN PAGINA SIGUIENTE',
            'VIENE DE PAGINA ANTERIOR',
            'Banco Credicoop Cooperativo',
            'Ctro. de Contacto Telefonico',
            'Calidad de Servicios',
            'Sitio de Internet',
            'Cuenta Corriente',
            'FECHA   COMBTE',
            'DENOMINACION',
            'TOTAL IMPUESTO',
            'LIQUIDACION',
            'DEBITOS AUTOMATICOS',
            'REINT X USO DE TARJ.CAB DEBITO',
            'REINTEGRO POR USO CABAL DEBITO',
            'REPARTO POR USO CABAL',
            'REINTEGRO POR USO DE TARJ.CAB DEBITO',
            'DEPOSITO',
            'SUELDO',
            'ESPECIAL',
            'PERIODICO',
            'SUCUR'
        ]

        def is_footer_line(line):
            return any(keyword in line for keyword in footer_keywords)

        # Start parsing after the transaction table header
        for line in lines:
            # Detect the start of the transaction table
            if not parsing_transactions:
                if 'FECHA' in line and 'DESCRIPCION' in line and 'DEBITO' in line and 'CREDITO' in line:
                    parsing_transactions = True
                continue  # Skip until we find the header

            # Stop parsing if we reach end of transactions
            if any(term in line for term in ['SALDO AL', 'DENOMINACION', 'TOTAL IMPUESTO', 'LIQUIDACION']):
                if current_row:
                    # Remove the helper key before appending
                    del current_row['continuation_lines_remaining']
                    rows.append(current_row)
                    current_row = None
                break

            line = line.rstrip()

            # Skip empty lines or lines with only underscores or dashes
            if not line.strip() or re.match(r'^[_\-]+$', line.strip()):
                continue

            # Check if line starts with a date
            date_match = date_regex.match(line)
            if date_match:
                # If we have a current_row, save it
                if current_row:
                    del current_row['continuation_lines_remaining']
                    rows.append(current_row)

                # Start a new transaction
                current_row = {
                    'FECHA': date_match.group(1),
                    'COMBTE': '',
                    'DESCRIPCION': '',
                    'DEBITO': '',
                    'CREDITO': '',
                    'SALDO': ''
                }

                rest_of_line = line[date_match.end():]

                # Try to extract COMBTE: first word if numeric
                combte_match = re.match(r'^(\d+)\s+', rest_of_line)
                if combte_match:
                    current_row['COMBTE'] = combte_match.group(1)
                    rest_of_line = rest_of_line[combte_match.end():]
                else:
                    current_row['COMBTE'] = ''

                # Extract amounts at the end of the line
                amount_match = amount_regex.search(rest_of_line)
                if amount_match:
                    amounts = [amt for amt in amount_match.groups() if amt]
                    description = rest_of_line[:amount_match.start()].strip()
                else:
                    amounts = []
                    description = rest_of_line.strip()

                current_row['DESCRIPCION'] = description

                # Assign amounts based on COMBTE presence
                if len(amounts) == 1:
                    if current_row['COMBTE']:
                        current_row['DEBITO'] = amounts[0]
                    else:
                        current_row['CREDITO'] = amounts[0]
                elif len(amounts) == 2:
                    if current_row['COMBTE']:
                        current_row['DEBITO'] = amounts[0]
                        current_row['SALDO'] = amounts[1]
                    else:
                        current_row['CREDITO'] = amounts[0]
                        current_row['SALDO'] = amounts[1]
                elif len(amounts) == 3:
                    current_row['DEBITO'] = amounts[0]
                    current_row['CREDITO'] = amounts[1]
                    current_row['SALDO'] = amounts[2]

                # Initialize continuation lines remaining
                current_row['continuation_lines_remaining'] = 1  # Limit to 1 continuation line
                continue

            else:
                # Check if it's a continuation line (indented)
                continuation_match = re.match(r'^\s+(.*)', line)
                if continuation_match and current_row:
                    # Avoid appending lines that are likely footers or unrelated
                    continuation_text = continuation_match.group(1).strip()
                    if is_footer_line(continuation_text):
                        continue  # Skip footer lines
                    if current_row.get('continuation_lines_remaining', 0) > 0:
                        # Append to description with newline
                        current_row['DESCRIPCION'] += '\n' + continuation_text
                        # Decrement continuation lines remaining
                        current_row['continuation_lines_remaining'] -= 1
                    continue  # Skip further processing for continuation lines

                # If the line doesn't start with a date and isn't indented, it's non-transactional; skip
                continue

        # Add the last transaction if exists
        if current_row:
            del current_row['continuation_lines_remaining']
            rows.append(current_row)

        return convert_to_canonical_format(rows)
