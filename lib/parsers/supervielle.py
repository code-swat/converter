import re
from typing import List, Dict

def convert_to_canonical_format(data: Dict) -> Dict:
    canonical_rows = []

    for row in data:
        saldo = row["Saldo"]
        if saldo:
            saldo = float(saldo.rstrip('-').replace('.', '').replace(',', '.'))
        else:
            saldo = ""

        canonical_row = {
            "FECHA": row["Fecha"],
            "DETALLE": row["Concepto"],
            "REFERENCIA": row["Referencia"],
            "DEBITOS": float(row["Débito"].replace('.', '').replace(',', '.')) if row["Débito"] else "", 
            "CREDITOS": float(row["Crédito"].replace('.', '').replace(',', '.')) if row["Crédito"] else "",
            "SALDO": saldo * -1 if "-" in row["Saldo"] else saldo
        }

        canonical_rows.append(canonical_row)

    return canonical_rows

class SupervielleParser:
    def parse_currency(self, s: str) -> float:
        """
        Converts a Spanish-formatted currency string to a float.
        Handles negative numbers indicated by a trailing minus sign.
        """
        s = s.strip()
        is_negative = False
        if s.endswith('-'):
            is_negative = True
            s = s[:-1]  # Remove the trailing minus sign
        s = s.replace('.', '').replace(',', '.')
        try:
            value = float(s)
            return -value if is_negative else value
        except ValueError:
            return None

    def parse(self, data: List[str]) -> List[List[Dict[str, str]]]:
        accounts = []  # List to hold all accounts
        current_account = []  # Current account's transactions
        in_subtotal = False
        in_entries = False

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
            # Check for "Saldo del período anterior" to start a new account
            if "Saldo del período anterior" in line:
                # If there's an existing account being processed, add it to accounts
                if current_account:
                    accounts.append(convert_to_canonical_format(current_account))
                    current_account = []
                in_entries = False  # Reset entries flag for new account
                in_subtotal = False  # Reset subtotal flag for new account
                # Extract the saldo
                match = re.search(r"Saldo del período anterior\s+([\d.,]+-?)", line)
                if match:
                    saldo = match.group(1)
                    current_account.append({
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
                    # If "Saldo del período anterior" is found but saldo is not parsed, skip
                    pass
                i += 1
                continue

            if in_entries:
                # Check for "SALDO PERIODO ACTUAL"
                if "SALDO PERIODO ACTUAL" in line:
                    # Finish the current account
                    if current_account:
                        accounts.append(convert_to_canonical_format(current_account))
                        current_account = []
                    i += 1
                    continue
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
                    # Extract amounts at the end of the line, possibly with negative saldo
                    # Pattern: amount, then saldo which may end with '-'
                    num_pattern = r'([\d.,]+)\s+([\d.,]+-?)$'
                    num_match = re.search(num_pattern, rest_of_line)
                    if num_match:
                        amount_str = num_match.group(1)
                        saldo_str = num_match.group(2)
                        # Remove the amounts from rest_of_line
                        rest_of_line_no_amounts = rest_of_line[:num_match.start()].strip()
                        # Extract referencia
                        # Updated pattern to include possible asterisks after digits
                        ref_pattern = r'(.*?)(R \d+\**|\d+\**)$'
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
                            ignore_lines = ["Imp Ley 25413", "SUBTOTAL", "SALDO PERIODO ACTUAL", "Saldo del período anterior"]
                            if not next_line or re.match(r"\d{2}/\d{2}/\d{2}", next_line) or any(ignore_line in next_line for ignore_line in ignore_lines):
                                break
                            else:
                                concepto_lines.append(next_line)
                                i += 1
                        concepto_full = '\n'.join(concepto_lines)
                        amount_float = self.parse_currency(amount_str)
                        saldo_float = self.parse_currency(saldo_str)
                        # Determine if Débito or Crédito
                        is_credit = False
                        is_debit = False
                        if previous_saldo_float is not None and saldo_float is not None and amount_float is not None:
                            # Check for Crédito: previous_saldo + amount == current_saldo
                            if abs((previous_saldo_float + amount_float) - saldo_float) < 0.01:
                                is_credit = True
                            # Check for Débito: previous_saldo - amount == current_saldo
                            if abs((previous_saldo_float - amount_float) - saldo_float) < 0.01:
                                is_debit = True
                        # Assign values based on determination
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
                        current_account.append(entry)
                        previous_saldo_float = saldo_float
                        continue
                    else:
                        i += 1
                        continue
                else:
                    i += 1
                    continue
            else:
                # Not currently in an account's entries; skip
                i += 1
                continue
            i += 1

        # After processing all lines, add the last account if it exists
        if current_account:
            accounts.append(convert_to_canonical_format(current_account))

        return accounts


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