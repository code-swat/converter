import re
from typing import List, Dict
import streamlit as st
def convert_to_canonical_format(data: Dict) -> Dict:
    canonical_rows = []

    for row in data:
        canonical_row = {
            "FECHA": row["Fecha"],
            "DETALLE": row["Concepto"],
            "REFERENCIA": row["Referencia"],
            "DEBITOS": float(row["Débito"].replace('.', '').replace(',', '.')) if row["Débito"] else "", 
            "CREDITOS": float(row["Crédito"].replace('.', '').replace(',', '.')) if row["Crédito"] else "",
            "SALDO": float(row["Saldo"].replace('.', '').replace(',', '.')) if row["Saldo"] else ""
        }

        canonical_rows.append(canonical_row)

    return canonical_rows

class SupervielleParser:
    def parse_currency(self, s: str) -> float:
        """Converts a Spanish-formatted currency string to a float."""
        s = s.replace('.', '').replace(',', '.')
        try:
            return float(s)
        except ValueError:
            return None

    def parse(self, data: List[str]) -> List[Dict]:
        entries = []
        in_subtotal = False
        in_entries = False
        stop_parsing = False

        previous_saldo_float = None

        # Combine all pages into a single list of lines
        lines = []
        for page in data:
            page_lines = page.split('\n')
            lines.extend(page_lines)

        i = 0
        while i < len(lines):
            line = lines[i].strip()
            # Skip empty lines
            if not line:
                i += 1
                continue
            if stop_parsing:
                break
            if not in_entries:
                # Check for "Saldo del período anterior"
                if "Saldo del período anterior" in line:
                    # Extract the saldo
                    match = re.search(r"Saldo del período anterior\s+([\d.,]+)", line)
                    if match:
                        saldo = match.group(1)
                        entries.append({
                            "Fecha": "",
                            "Concepto": "Saldo del período anterior",
                            "Referencia": "",
                            "Débito": "",
                            "Crédito": "",
                            "Saldo": saldo
                        })
                        previous_saldo_float = self.parse_currency(saldo)
                        in_entries = True
                    else:
                        i += 1
                    continue
                else:
                    i += 1
                    continue
            else:
                # Check for "SALDO PERIODO ACTUAL"
                if "SALDO PERIODO ACTUAL" in line:
                    stop_parsing = True
                    break
                # Check for "SUBTOTAL"
                if line.startswith("SUBTOTAL"):
                    if not in_subtotal:
                        in_subtotal = True
                    else:
                        in_subtotal = False
                    i += 1
                    continue
                if in_subtotal:
                    i += 1
                    continue
                # Process transaction lines
                match = re.match(r"(\d{2}/\d{2}/\d{2})\s+(.*)", line)
                if match:
                    fecha = match.group(1)
                    rest_of_line = match.group(2)
                    # Extract amounts at the end of the line
                    num_pattern = r'([\d.,]+)\s+([\d.,]+)$'
                    num_match = re.search(num_pattern, rest_of_line)
                    if num_match:
                        amount_str = num_match.group(1)
                        saldo_str = num_match.group(2)
                        # Remove the amounts from rest_of_line
                        rest_of_line_no_amounts = rest_of_line[:num_match.start()].strip()
                        # Extract referencia
                        ref_pattern = r'(.*?)(R \d+|\d{10})$'
                        ref_match = re.match(ref_pattern, rest_of_line_no_amounts)
                        if ref_match:
                            concepto = ref_match.group(1).strip()
                            referencia = ref_match.group(2).strip()
                        else:
                            concepto = rest_of_line_no_amounts
                            referencia = ""
                        # Collect additional concepto lines
                        concepto_lines = [concepto]
                        i += 1
                        while i < len(lines):
                            next_line = lines[i].strip()
                            if not next_line or re.match(r"\d{2}/\d{2}/\d{2}", next_line) or next_line.startswith("SUBTOTAL") or "SALDO PERIODO ACTUAL" in next_line:
                                break
                            else:
                                concepto_lines.append(next_line)
                                i += 1
                        concepto_full = '\n'.join(concepto_lines)
                        amount_float = self.parse_currency(amount_str)
                        saldo_float = self.parse_currency(saldo_str)
                        # Determine if Débito or Crédito
                        is_credit = abs((previous_saldo_float + amount_float) - saldo_float) < 0.01
                        is_debit = abs((previous_saldo_float - amount_float) - saldo_float) < 0.01
                        if is_credit and not is_debit:
                            entry = {
                                "Fecha": fecha,
                                "Concepto": concepto_full,
                                "Referencia": referencia,
                                "Débito": "",
                                "Crédito": amount_str,
                                "Saldo": saldo_str
                            }
                        elif is_debit and not is_credit:
                            entry = {
                                "Fecha": fecha,
                                "Concepto": concepto_full,
                                "Referencia": referencia,
                                "Débito": amount_str,
                                "Crédito": "",
                                "Saldo": saldo_str
                            }
                        else:
                            # Ambiguous transaction; cannot determine Débito or Crédito
                            entry = {
                                "Fecha": fecha,
                                "Concepto": concepto_full,
                                "Referencia": referencia,
                                "Débito": "",
                                "Crédito": "",
                                "Saldo": saldo_str
                            }
                        entries.append(entry)
                        previous_saldo_float = saldo_float
                        continue
                    else:
                        i += 1
                        continue
                else:
                    i += 1
                    continue
            i += 1
        return convert_to_canonical_format(entries)


expected_output = [
  {
    "Fecha": "",
    "Concepto": "Saldo del período anterior",
    "Referencia": "",
    "Débito": "",
    "Crédito": "",
    "Saldo": "4.734.369,71"
  },
  {
    "Fecha": "03/05/24",
    "Concepto": "Débito Automáticode Servicio\nINFORMYTELECOMSA Id:218232\nPres:INTERNET Ref:R 700301492189",
    "Referencia": "R 70030149",
    "Débito": "7.260,00",
    "Crédito": "",
    "Saldo": "4.727.109,71"
  },
  {
    "Fecha": "03/05/24",
    "Concepto": "Débito Automáticode Servicio\nINFORMYTELECOMSA Id:218232\nPres:INTERNET Ref:R 700301496615",
    "Referencia": "R 70030149",
    "Débito": "6.858,00",
    "Crédito": "",
    "Saldo": "4.720.251,71"
  },
  {
    "Fecha": "03/05/24",
    "Concepto": "Crédito por Transferencia\nCANGELOSI, SOFIA 6 27326277458\nRef:VAR- BANCO SUPERVIELLE S.A.",
    "Referencia": "0666308298",
    "Débito": "",
    "Crédito": "332.000,00",
    "Saldo": "5.052.251,71"
  }
]