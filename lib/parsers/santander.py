import re
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
    def detect_format(self, data: List[str]) -> str:
        """Detect if it's old format (pesos) or new format ($) by checking first 100 lines"""
        # Join first few pages to get enough content for detection
        first_pages = data[:3] if len(data) > 3 else data
        text = '\n'.join(first_pages)
        lines = text.split('\n')[:100]  # Check first 100 lines

        # Look for "pesos" followed by a number pattern
        pesos_pattern = re.compile(r'pesos\s+[\d.,]+')

        for line in lines:
            if pesos_pattern.search(line.lower()):
                return "old"

        return "new"

    def parse(self, data: List[str]) -> List[List[Dict[str, str]]]:
        format_type = self.detect_format(data)

        if format_type == "old":
            return self.parse_old_format(data)
        else:
            return self.parse_new_format(data)

    def parse_old_format(self, data: List[str]) -> List[List[Dict[str, str]]]:
        """Parse old format with 'pesos' indicators"""
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
            if 'Saldo total' in line and i+1 < n and self.is_amount_line_old(lines[i+1]):
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
                # Next line should have amount (pesos or $)
                if i+1 < n and self.is_amount_line_old(lines[i+1]):
                    saldo_en_cuenta = self.format_amount(self.parse_amount_old(lines[i+1]))
                    transactions.append({
                        'Fecha': current_date,
                        'Comprobante': comprobante,
                        'Movimiento': movimiento,
                        'Débito': debito,
                        'Crédito': credito,
                        'Saldo en cuenta': saldo_en_cuenta
                        })
                    previous_saldo = self.parse_amount_old(lines[i+1])
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
            while i < n and not self.is_amount_line_old(lines[i]) and not re.match(r'^\d{2}/\d{2}/\d{2}$', lines[i].strip()) and not re.match(r'^\d{1,15}$', lines[i].strip()):
                movimiento_lines.append(lines[i].strip())
                i += 1
            movimiento = '\n'.join(movimiento_lines).strip()

            # Collect Débito/Credito and Saldo en cuenta
            debito_credito = ''
            saldo = ''
            if i < n and self.is_amount_line_old(lines[i]):
                debito_credito = lines[i].strip()
                i += 1
            if i < n and self.is_amount_line_old(lines[i]):
                saldo = lines[i].strip()
                i += 1

            debito_amount = self.parse_amount_old(debito_credito) if debito_credito else None
            saldo_amount = self.parse_amount_old(saldo) if saldo else None

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

    def parse_new_format(self, data: List[str]) -> List[List[Dict[str, str]]]:
        """Parse new format with '$' indicators"""
        data_str = self.clean_pages_new(data)
        lines = data_str.split('\n')

        transactions = []
        i = 0
        n = len(lines)
        date_regex = re.compile(r'^(\d{2}/\d{2}/\d{2})')

        # Find and process Saldo Inicial
        start_index = -1
        for idx in range(n):
            if 'Saldo Inicial' in lines[idx]:
                start_index = idx
                break

        if start_index == -1:
            raise ValueError("Could not find 'Saldo Inicial' in the data")

        saldo_line_index = -1
        saldo_inicial_amount = None
        for j in range(start_index + 1, min(start_index + 3, n)):
            if self.is_amount_line_new(lines[j]):
                saldo_inicial_amount = self.parse_amount_new(lines[j])
                saldo_line_index = j
                break

        if saldo_inicial_amount is None:
            raise ValueError("Could not find Saldo Inicial amount")

        transactions.append({
            'Fecha': '', # Per desired output
            'Comprobante': '',
            'Movimiento': 'Saldo Inicial',
            'Débito': '',
            'Crédito': '',
            'Saldo en cuenta': self.format_amount(saldo_inicial_amount)
        })
        previous_saldo = saldo_inicial_amount
        i = saldo_line_index + 1

        # --- New Main Transaction Loop ---
        while i < n:
            line = lines[i].strip()
            if not line:
                i += 1
                continue

            # A transaction starts with a date, either on its own line or with other info
            date_match = date_regex.match(line)
            if not date_match:
                i += 1
                continue

            # We found a line that starts a transaction
            fecha = date_match.group(1)
            line_content = line[len(fecha):].strip()

            comprobante = ''
            movimiento_lines = []

            # Heuristic: if content after date starts with a long number, it's a comprobante
            parts = line_content.split(maxsplit=1)
            if parts and parts[0].isdigit() and 4 <= len(parts[0]) <= 15:
                comprobante = parts[0]
                if len(parts) > 1 and parts[1]:
                    movimiento_lines.append(parts[1])
            elif line_content:
                movimiento_lines.append(line_content)

            i += 1 # Consume the date line

            # Collect subsequent movement lines and a potential comprobante
            while i < n:
                line = lines[i].strip()
                if not line:
                    i+=1
                    continue

                # Stop condition: we've reached amounts or a new transaction date
                if self.is_amount_line_new(line) or date_regex.match(line):
                    break

                # Comprobante check: is it a numeric-only line and we don't have a comprobante yet?
                if not comprobante and line.isdigit() and 4 <= len(line) <= 15:
                    comprobante = line
                else:
                    movimiento_lines.append(line)

                i += 1

            # Collect the two amount lines
            amounts = []
            if i < n and self.is_amount_line_new(lines[i].strip()):
                amounts.append(lines[i].strip())
            if i + 1 < n and self.is_amount_line_new(lines[i+1].strip()):
                amounts.append(lines[i+1].strip())

            # Process the transaction if we have the amounts
            if len(amounts) == 2:
                movimiento = '\n'.join(movimiento_lines)
                transaction_amount_str, new_saldo_str = amounts

                transaction_amount = self.parse_amount_new(transaction_amount_str)
                new_saldo = self.parse_amount_new(new_saldo_str)

                if transaction_amount is None or new_saldo is None or previous_saldo is None:
                    raise ValueError(f"Failed to parse amounts for date {fecha}")

                credit_calc = abs(previous_saldo + transaction_amount - new_saldo)
                debit_calc = abs(previous_saldo - transaction_amount - new_saldo)
                debito, credito = '', ''

                if credit_calc < 0.01:
                    credito = self.format_amount(transaction_amount)
                elif debit_calc < 0.01:
                    debito = self.format_amount(transaction_amount)
                else:
                    raise ValueError(f"Balance validation failed for date {fecha}")

                transactions.append({
                    'Fecha': fecha,
                    'Comprobante': comprobante,
                    'Movimiento': movimiento,
                    'Débito': debito,
                    'Crédito': credito,
                    'Saldo en cuenta': self.format_amount(new_saldo)
                })
                previous_saldo = new_saldo
                i += 2 # Consume the two amount lines

        return [convert_to_canonical_format(transactions)]

    def is_amount_line_old(self, line):
        """Check if a line contains an amount in old format (with 'pesos')"""
        line_lower = line.lower().strip()
        return 'pesos' in line_lower

    def is_amount_line_new(self, line):
        """Check if a line contains an amount in new format (with '$')"""
        line_stripped = line.strip()

        # Amount lines should start with $ or -$ and be primarily numeric
        # Examples: "$ 640.322,55", "-$ 100,00"
        amount_pattern = re.compile(r'^\s*-?\$\s*[\d.,]+\s*$')
        result = bool(amount_pattern.match(line_stripped))

        return result

    def parse_amount_old(self, amount_str):
        """Parse amount in old format"""
        amount_str = amount_str.replace(' ', '').replace('pesos', '').replace('menos', '-')
        amount_str = amount_str.replace('.', '').replace(',', '.')
        try:
            return float(amount_str)
        except ValueError:
            return None

    def parse_amount_new(self, amount_str):
        """Parse amount in new format"""
        original = amount_str
        amount_str = amount_str.replace(' ', '')

        # Handle negative amounts in new format (-$)
        if '-$' in amount_str:
            amount_str = amount_str.replace('-$', '-').replace('$', '')
        else:
            # Handle positive amounts with $
            amount_str = amount_str.replace('$', '')

        # Clean up number formatting (thousands separators and decimal point)
        amount_str = amount_str.replace('.', '').replace(',', '.')

        try:
            result = float(amount_str)
            return result
        except ValueError:
            st.write(f"Failed to parse '{original}' (cleaned: '{amount_str}')")
            return None

    def format_amount(self, amount):
        if amount is None:
            return ''
        return "{:,.2f}".format(amount).replace(',', ' ').replace('.', ',').replace(' ', '.')

    def clean_pages(self, pages):
        """Clean pages for old format"""
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

    def clean_pages_new(self, pages):
        """Clean pages for new format"""
        # For new format, let's be more aggressive about finding the transaction data
        lines = []

        for page_idx, page in enumerate(pages):
            # Check if this page contains transaction data
            if 'Saldo Inicial' in page or 'Movimiento' in page or any(date_pattern in page for date_pattern in ['01/08/24', '02/08/24', '03/08/24']):
                page_lines = page.split('\n')

                # Find where the actual transaction data starts
                start_capturing = False
                for line_idx, line in enumerate(page_lines):
                    line_stripped = line.strip()

                    # Look for various markers that indicate transaction section start
                    if any(marker in line.lower() for marker in ['movimientos en pesos', 'saldo inicial', 'fecha', 'comprobante']):
                        start_capturing = True

                    # Stop at certain end markers
                    if start_capturing and any(marker in line.lower() for marker in ['saldo total', 'movimientos en dólares', 'legales', 'otros fondos']):
                        break

                    if start_capturing and line_stripped:  # Only add non-empty lines
                        lines.append(line_stripped)

        return '\n'.join(lines)
