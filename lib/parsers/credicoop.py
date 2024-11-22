import re
from typing import Dict, List

def convert_to_canonical_format(data: Dict) -> Dict:
    canonical_rows = []

    for row in data:
        canonical_row = {
            "FECHA": row["FECHA"],
            "DETALLE": row["DESCRIPCION"],
            "REFERENCIA": row["COMBTE"],
            "DEBITOS": float(row["DEBITO"].replace('.', '').replace(',', '.')) if row["DEBITO"] else "", 
            "CREDITOS": float(row["CREDITO"].replace('.', '').replace(',', '.')) if row["CREDITO"] else "",
            "SALDO": float(row["SALDO"].replace('.', '').replace(',', '.')) if row["SALDO"] else ""
        }

        canonical_rows.append(canonical_row)

    return canonical_rows

class CredicoopParser:
    # Configurable field positions (start and end indices)
    FIELD_CONFIG = {
        "FECHA": (0, 9),       # Adjusted to capture 'dd/mm/aa'
        "COMBTE": (9, 16),
        "DESCRIPCION": (16, 57),
        "DEBITO": (57, 74),
        "CREDITO": (74, 92),
        "SALDO": (92, 109),     # Till end of line
    }

    DATE_REGEX = re.compile(r'^\d{2}/\d{2}/\d{2}$')

    def parse(self, data: List[str]) -> List[List[Dict[str, str]]]:
        # Combine all pages into a single list of lines
        lines = []
        for page in data:
            lines.extend(page.split('\n'))

        entries = []
        saldo_anterior = None
        balance = None
        processing = False
        skip_until_headers = False
        i = 0

        # Regular expression to match the header line
        header_regex = re.compile(r'^FECHA\s+COMBTE\s+DESCRIPCION\s+DEBITO\s+CREDITO\s+SALDO')

        # Function to format amounts
        def format_amount(value):
            if value is None:
                return ""
            # Ensure consistent decimal separator
            amount_str = "{:,.2f}".format(abs(value)).replace(',', 'X').replace('.', ',').replace('X', '.')
            return f"-{amount_str}" if value < 0 else amount_str

        # Function to parse currency strings to float
        def parse_currency(value):
            try:
                return float(value.replace('.', '').replace(',', '.'))
            except:
                return None

        while i < len(lines):
            line = lines[i].strip()

            if not processing:
                if "SALDO ANTERIOR" in line:
                    processing = True
                    # Extract the SALDO ANTERIOR value
                    parts = line.split()
                    saldo_value_str = parts[-1]
                    saldo_anterior = parse_currency(saldo_value_str)
                    if saldo_anterior is None:
                        raise ValueError(f"Invalid SALDO ANTERIOR value: {saldo_value_str}")
                    balance = saldo_anterior
                    entries.append({
                        "FECHA": "",
                        "COMBTE": "",
                        "DESCRIPCION": "SALDO ANTERIOR",
                        "DEBITO": "",
                        "CREDITO": "",
                        "SALDO": format_amount(balance)
                    })
            else:
                if "CONTINUA EN PAGINA SIGUIENTE" in line:
                    skip_until_headers = True
                elif skip_until_headers:
                    if header_regex.match(line):
                        skip_until_headers = False
                    # Else, continue skipping
                elif not line:
                    # Ignore blank lines
                    pass
                elif "SALDO AL" in line:
                    # Extract the date and balance for SALDO FINAL
                    # Example: "SALDO AL 31/05/24 9.910.825,60"
                    saldo_final_match = re.search(r'SALDO AL\s+(\d{2}/\d{2}/\d{2})\s+([\d\.,\-]+)', line)
                    if saldo_final_match:
                        date = saldo_final_match.group(1)
                        saldo_final_str = saldo_final_match.group(2)
                        saldo_final = parse_currency(saldo_final_str)
                        if saldo_final is None:
                            raise ValueError(f"Invalid SALDO FINAL value: {saldo_final_str}")
                        entries.append({
                            "FECHA": date,
                            "COMBTE": "",
                            "DESCRIPCION": "SALDO FINAL",
                            "DEBITO": "",
                            "CREDITO": "",
                            "SALDO": format_amount(saldo_final)
                        })
                    else:
                        raise ValueError(f"Invalid SALDO FINAL line format: {line}")
                    break  # Assuming SALDO FINAL is the end
                else:
                    # Check if line starts with a valid date
                    fecha_str = line[self.FIELD_CONFIG["FECHA"][0]:self.FIELD_CONFIG["FECHA"][1]].strip()
                    if self.DATE_REGEX.match(fecha_str):
                        # Start of a new entry
                        combte_str = line[self.FIELD_CONFIG["COMBTE"][0]:self.FIELD_CONFIG["COMBTE"][1]].strip()
                        descripcion_str = line[self.FIELD_CONFIG["DESCRIPCION"][0]:self.FIELD_CONFIG["DESCRIPCION"][1]].strip()
                        debito_str = line[self.FIELD_CONFIG["DEBITO"][0]:self.FIELD_CONFIG["DEBITO"][1]].strip()
                        credito_str = line[self.FIELD_CONFIG["CREDITO"][0]:self.FIELD_CONFIG["CREDITO"][1]].strip()
                        saldo_str = line[self.FIELD_CONFIG["SALDO"][0]:].strip()

                        current_entry = {
                            "FECHA": fecha_str,
                            "COMBTE": combte_str,
                            "DESCRIPCION": descripcion_str,
                            "DEBITO": "",
                            "CREDITO": "",
                            "SALDO": ""
                        }

                        # Check for continuation lines
                        j = i + 1
                        while j < len(lines):
                            next_line = lines[j]
                            next_fecha = next_line[self.FIELD_CONFIG["FECHA"][0]:self.FIELD_CONFIG["FECHA"][1]].strip()
                            if not self.DATE_REGEX.match(next_fecha) and next_line.strip() and "SALDO AL" not in next_line.strip():
                                # Continuation line
                                continuation_descr = next_line[self.FIELD_CONFIG["DESCRIPCION"][0]:self.FIELD_CONFIG["DESCRIPCION"][1]].strip()
                                if continuation_descr:
                                    current_entry["DESCRIPCION"] += "\n" + continuation_descr
                                j += 1
                                i = j - 1  # Update main loop index
                            else:
                                break

                        # Parse amounts
                        debito = parse_currency(debito_str) if debito_str else None
                        credito = parse_currency(credito_str) if credito_str else None
                        saldo = parse_currency(saldo_str) if saldo_str else None

                        # Update balance
                        if debito is not None:
                            balance -= debito
                        if credito is not None:
                            balance += credito

                        # Check balance if saldo is provided
                        if saldo is not None:
                            if abs(balance - saldo) > 0.01:
                                raise ValueError(f"Balance mismatch at line {i+1}: calculated {balance}, reported {saldo}")
                                #st.write(f"Balance mismatch at line {i+1}: calculated {balance}, reported {saldo}")
                        else:
                            saldo = balance

                        # Assign formatted amounts
                        current_entry["DEBITO"] = format_amount(debito) if debito is not None else ""
                        current_entry["CREDITO"] = format_amount(credito) if credito is not None else ""
                        current_entry["SALDO"] = format_amount(saldo) if saldo is not None else ""

                        entries.append(current_entry)
                    else:
                        #st.write(f"Ignoring line {i+1}: fecha_str {fecha_str} - {lines[i]}")
                        # Line does not start with a valid date and is not a continuation
                        # Ignore or handle as needed
                        pass

            i += 1

        return [convert_to_canonical_format(entries)]
