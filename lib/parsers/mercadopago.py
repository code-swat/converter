import re
from typing import Dict, List, Optional
from decimal import Decimal

def convert_to_canonical_format(data: Dict) -> Dict:
    canonical_rows = []

    for row in data:
        valor = float(row["Valor"].replace('.', '').replace(',', '.')) if row["Valor"] else 0

        canonical_row = {
            "FECHA": row["Fecha"],
            "DETALLE": row["Descripción"],
            "REFERENCIA": row["ID"],
            "DEBITOS": valor * -1 if valor < 0 else "",
            "CREDITOS": valor if valor > 0 else "",
            "SALDO": float(row["Saldo"].replace('.', '').replace(',', '.')) if row["Saldo"] else ""
        }

        canonical_rows.append(canonical_row)

    return canonical_rows


class MercadoPagoParser:
    def __init__(self):
        self.current_balance = Decimal('0')
        self.date_pattern = r'\d{2}-\d{2}-\d{2}\d{2}'
        self.currency_pattern = r'\$\s*-?\d+(?:(?:\.\d{3})*,\d{2}|,\d{2})'

    def _parse_currency(self, value: str) -> str:
        """Convert currency format '$ 1.234,56' or '$ -1.234,56' to '1.234,56' or '-1.234,56'"""
        return value.replace('$', '').strip()

    def _validate_balance(self, value: str, balance: str) -> None:
        """Validate that current_balance + value equals the expected balance"""
        value_decimal = Decimal(value.replace('.', '').replace(',', '.'))
        balance_decimal = Decimal(balance.replace('.', '').replace(',', '.'))
        self.current_balance += value_decimal

        if abs(self.current_balance - balance_decimal) > Decimal('0.01'):
            raise ValueError(f"Balance mismatch: Expected {balance_decimal}, got {self.current_balance}")

    def _find_initial_balance(self, text: str) -> Optional[str]:
        """Find the initial balance in the text"""
        match = re.search(r'Saldo inicial:\s*' + self.currency_pattern, text)
        if match:
            balance = self._parse_currency(match.group().split(':')[1])
            self.current_balance = Decimal(balance.replace('.', '').replace(',', '.'))
            return balance
        return None

    def _extract_description(self, text: str, start_idx: int, end_idx: int) -> str:
        """Extract description from transaction text, handling multiline descriptions"""
        # Get the text segment we're working with
        segment = text[start_idx:end_idx]

        # Split into lines and remove empty ones
        lines = [line.strip() for line in segment.split('\n') if line.strip()]

        # Find the line with the ID (8 digits)
        id_pattern = r'\d{8}'
        description_lines = []

        for i, line in enumerate(lines):
            line = re.sub(r'^\d{2}-\d{2}-\d{4}\s*', '', line)
            # If line contains ID pattern, keep the text before it
            if re.search(id_pattern, line):
                # Split the line at the ID pattern and keep the text before it
                pre_id_text = re.split(id_pattern, line)[0].strip()
                if pre_id_text:
                    description_lines.append(pre_id_text)
                break

            description_lines.append(line)

        return ' '.join(description_lines).strip()

    def _extract_transaction(self, text: str, start_idx: int) -> tuple[Optional[Dict[str, str]], int]:
        """Extract a single transaction starting from the given index"""
        # Find next date
        date_match = re.search(self.date_pattern, text[start_idx:])
        if not date_match:
            return None, len(text)

        transaction_start = start_idx + date_match.start()

        # Find next date to determine transaction end
        next_date_match = re.search(self.date_pattern, text[transaction_start + 10:])
        transaction_end = transaction_start + 10 + next_date_match.start() if next_date_match else len(text)

        transaction_text = text[transaction_start:transaction_end]

        # Extract required fields
        date = date_match.group().replace('-', '/')

        # Extract description using the new method
        description = self._extract_description(text, transaction_start, transaction_end)

        # Find ID (numeric sequence)
        id_match = re.search(r'\d{11}', transaction_text)
        id_value = id_match.group() if id_match else ""

        # Find currency values (should be last two numbers in transaction)
        currency_matches = re.finditer(self.currency_pattern, transaction_text)
        currency_values = [self._parse_currency(m.group()) for m in currency_matches]

        if len(currency_values) >= 2:
            valor = currency_values[-2]
            saldo = currency_values[-1]

            # Validate balance
            #self._validate_balance(valor, saldo)

            return {
                "Fecha": date,
                "Descripción": description,
                "ID": id_value,
                "Valor": valor,
                "Saldo": saldo
            }, transaction_start + 10

        return None, transaction_start + 10

    def parse(self, data: List[str]) -> List[List[Dict[str, str]]]:
        result = []

        for page in data:
            page_transactions = []

            # Handle initial balance for first page
            if len(result) == 0:
                initial_balance = self._find_initial_balance(page)
                if initial_balance:
                    page_transactions.append({
                        "Fecha": "",
                        "Descripción": "Saldo inicial",
                        "ID": "",
                        "Valor": "",
                        "Saldo": initial_balance
                    })

            # Skip header section - find "DETALLE DE MOVIMIENTOS" first
            header_end_match = re.search(r'DETALLE DE MOVIMIENTOS', page)
            if header_end_match:
                current_pos = header_end_match.end()

                # Skip the column headers (Fecha, Descripción, ID, etc.)
                column_headers_end = page.find('\n', current_pos)
                if column_headers_end != -1:
                    current_pos = column_headers_end + 1
            else:
                current_pos = 0

            # Process transactions
            while current_pos < len(page):
                transaction, next_pos = self._extract_transaction(page, current_pos)
                if transaction:
                    page_transactions.append(transaction)
                current_pos = next_pos

            if page_transactions:
                result.append(page_transactions)

        return [convert_to_canonical_format([transaction for page in result for transaction in page])]