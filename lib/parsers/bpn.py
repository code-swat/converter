import streamlit as st
from typing import List, Dict
import re

def convert_to_canonical_format(data: Dict) -> Dict:
    canonical_rows = []

    for row in data:
        detalle = ""
        referencia = ""
        if row["Descripción"]:
            parts = [p for p in re.split(r'\s{2,}', row["Descripción"].strip()) if p]
            detalle = parts[0] if parts else ""
            referencia = parts[-1] if len(parts) > 1 else row["Comprobante"]
        
        canonical_row = {
            "FECHA": row["Fecha"],
            "DETALLE": detalle,
            "REFERENCIA": referencia,
            "DEBITOS": float(row["Débito"].replace('.', '').replace(',', '.')) if row["Débito"] else '', 
            "CREDITOS": float(row["Crédito"].replace('.', '').replace(',', '.')) if row["Crédito"] else '',
            "SALDO": float(row["Saldo"]) if row["Saldo"] else ''
        }

        canonical_rows.append(canonical_row)

    return canonical_rows

class BPNParser:
    def parse(self, data: List[str]) -> List[List[Dict[str, str]]]:
        transactions = []
        saldo_anterior = None
        saldo_actual = None
        parsing = False  # Flag to start parsing after "Saldo Anterior en $"

        # Concatenate all pages into one list of lines
        all_text = "\n".join(data)
        lines = all_text.split("\n")

        # Regular expressions for matching
        saldo_anterior_regex = re.compile(r"Saldo Anterior en \$\s*:\s*([-\d.,]+)")
        saldo_final_regex = re.compile(r"Saldo en \$\s*:\s*([-\d.,]+)")
        # Updated regex to capture Comprobante with alphanumerics and possible spaces
        transaction_regex = re.compile(
            r"^(?P<Fecha>\d{1,2}/\d{1,2}/\d{4})\s+"
            r"(?P<Descripción>.*?)\s{2,}"
            r"(?:(?P<Comprobante>[A-Za-z0-9\s]+?)\s{2,})?"
            r"(?P<Monto>[.\d,]+)?\s+"
            r"(?P<Saldo>[-.\d,]+)$"
        )

        for line in lines:
            line = line.strip()

            # Check for start of parsing
            if not parsing:
                saldo_anterior_match = saldo_anterior_regex.search(line)
                if saldo_anterior_match:
                    saldo_str = saldo_anterior_match.group(1)
                    saldo_anterior = self._parse_currency(saldo_str)
                    transactions.append({
                        "Fecha": "",
                        "Descripción": "Saldo Anterior",
                        "Comprobante": "",
                        "Débito": "",
                        "Crédito": "",
                        "Saldo": saldo_str.replace('.', '').replace(',', '.')
                    })
                    saldo_actual = saldo_anterior
                    parsing = True
                continue  # Skip lines until "Saldo Anterior en $"

            # Check for end of parsing
            saldo_final_match = saldo_final_regex.search(line)
            if saldo_final_match:
                break  # Stop parsing when "Saldo en $" is found

            # Match transaction lines
            transaction_match = transaction_regex.match(line)
            if transaction_match:
                fecha = transaction_match.group("Fecha")
                descripcion = transaction_match.group("Descripción").strip()
                comprobante = transaction_match.group("Comprobante") or ""
                monto_str = transaction_match.group("Monto") or ""
                saldo_str = transaction_match.group("Saldo").replace(".", "").replace(",", ".")
                
                # Parse saldo
                try:
                    saldo = float(saldo_str)
                except ValueError:
                    saldo = None  # Handle unexpected format

                # Parse monto
                monto = self._parse_currency(monto_str)

                # Determine if Débito or Crédito based on saldo difference
                if saldo is not None and saldo_actual is not None:
                    if saldo > saldo_actual:
                        # Crédito
                        debito = ""
                        credito = f"{monto_str}" if monto is not None else ""
                    else:
                        # Débito
                        debito = f"{monto_str}" if monto is not None else ""
                        credito = ""
                else:
                    debito = ""
                    credito = ""

                transaction = {
                    "Fecha": fecha,
                    "Descripción": descripcion,
                    "Comprobante": comprobante.strip(),
                    "Débito": debito,
                    "Crédito": credito,
                    "Saldo": saldo_str
                }

                transactions.append(transaction)

                # Update saldo_actual
                if saldo is not None:
                    saldo_actual = saldo

        return [convert_to_canonical_format(transactions)]

    def _parse_currency(self, amount_str: str) -> float:
        """
        Convert a currency string to a float.
        Example: "19.607,54" -> 19607.54
        """
        if not amount_str:
            return 0.0
        # Remove thousand separators and replace decimal comma with dot
        clean_str = amount_str.replace(".", "").replace(",", ".")
        try:
            return float(clean_str)
        except ValueError:
            return 0.0
