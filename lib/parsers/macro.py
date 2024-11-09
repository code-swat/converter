import streamlit as st
from typing import Dict, List
import re

class MacroParser:
    def parse(self, data: List[Dict]) -> List[Dict]:
        st.write("### MACRO PARSER")
        
        # Step 1: Extract and Sort Text Elements
        texts = []
        for element in data:
            text = element.get('text', '').strip()
            bbox = element.get('bbox', [])
            if not text:
                continue  # Skip empty texts
            # Handle bbox as list of points or flat list
            if isinstance(bbox, list):
                if all(isinstance(point, (list, tuple)) and len(point) >= 2 for point in bbox):
                    # bbox is a list of coordinate pairs
                    x_coords = [point[0] for point in bbox]
                    y_coords = [point[1] for point in bbox]
                elif all(isinstance(coord, (int, float)) for coord in bbox):
                    # bbox is a flat list of coordinates
                    if len(bbox) % 2 != 0:
                        st.warning(f"Invalid bbox format for text: {text}")
                        continue
                    x_coords = bbox[0::2]
                    y_coords = bbox[1::2]
                else:
                    st.warning(f"Invalid bbox structure for text: {text}")
                    continue
                x0 = min(x_coords)
                y0 = min(y_coords)
                texts.append({
                    'text': text,
                    'x0': x0,
                    'y0': y0
                })
            else:
                st.warning(f"Unexpected bbox type for text: {text}")
                continue

        if not texts:
            st.error("No valid text data found.")
            return []

        # Step 2: Sort texts by y0 (top to bottom) then x0 (left to right)
        texts.sort(key=lambda x: (x['y0'], x['x0']))

        # Step 3: Group texts into lines based on y0 proximity
        lines = self.group_texts_into_lines(texts, y_threshold=10)  # Adjust y_threshold as needed

        st.write(f"Total lines detected: {len(lines)}")

        # Step 4: Construct line strings
        line_strings = self.construct_line_strings(lines)

        st.write(f"Constructed {len(line_strings)} line strings.")

        # Step 5: Parse each line using regex
        parsed_data = self.parse_lines(line_strings)

        # Step 6: Display parsed data
        st.write("### Parsed Data:")
        st.json(parsed_data)
        return parsed_data

    def group_texts_into_lines(self, texts: List[Dict], y_threshold: int = 10) -> List[List[Dict]]:
        """
        Groups text elements into lines based on y-coordinate proximity.
        """
        lines = []
        current_line = []
        current_y = None

        for text in texts:
            if current_y is None:
                current_y = text['y0']
                current_line.append(text)
            else:
                if abs(text['y0'] - current_y) <= y_threshold:
                    current_line.append(text)
                else:
                    lines.append(current_line)
                    current_line = [text]
                    current_y = text['y0']
        if current_line:
            lines.append(current_line)

        return lines

    def construct_line_strings(self, lines: List[List[Dict]]) -> List[str]:
        """
        Constructs a complete line string by ordering texts within the line.
        """
        line_strings = []
        for line in lines:
            # Sort texts within the line by x0
            sorted_texts = sorted(line, key=lambda x: x['x0'])
            # Concatenate texts with spaces
            line_str = ' '.join([text['text'] for text in sorted_texts])
            line_strings.append(line_str)
        return line_strings

    def parse_lines(self, line_strings: List[str]) -> List[Dict]:
        """
        Parses each line string to extract transaction fields using regex.
        """
        parsed_data = []
        saldo_final_present = False  # Flag to identify SALDO FINAL

        for idx, line in enumerate(line_strings):
            st.write(f"Processing line {idx}: '{line}'")
            # Check for SALDO ULTIMO EXTRACTO
            if re.search(r"SALDO ULTIMO EXTRACTO", line, re.IGNORECASE):
                match = re.search(r"SALDO ULTIMO EXTRACTO AL\s*(\d{1,2}/\d{1,2}/\d{4})\s*([\d.,]+)", line, re.IGNORECASE)
                if match:
                    fecha = match.group(1)
                    saldo = match.group(2)
                    parsed_data.append({
                        "FECHA": fecha,
                        "DESCRIPCION": "SALDO ULTIMO EXTRACTO",
                        "REFERENCIA": "",
                        "DEBITOS": "",
                        "CREDITOS": "",
                        "SALDO": saldo
                    })
                    st.write(f"Extracted SALDO ULTIMO EXTRACTO: Fecha={fecha}, Saldo={saldo}")
                else:
                    st.warning(f"Could not parse SALDO ULTIMO EXTRACTO from line {idx}: '{line}'")
                continue

            # Check for SALDO FINAL
            if re.search(r"SALDO FINAL AL DIA", line, re.IGNORECASE):
                match = re.search(r"SALDO FINAL AL DIA\s*(\d{1,2}/\d{1,2}/\d{4})\s*([\d.,]+)", line, re.IGNORECASE)
                if match:
                    fecha = match.group(1)
                    saldo = match.group(2)
                    parsed_data.append({
                        "FECHA": fecha,
                        "DESCRIPCION": "SALDO FINAL",
                        "REFERENCIA": "",
                        "DEBITOS": "",
                        "CREDITOS": "",
                        "SALDO": saldo
                    })
                    st.write(f"Extracted SALDO FINAL: Fecha={fecha}, Saldo={saldo}")
                    saldo_final_present = True
                else:
                    st.warning(f"Could not parse SALDO FINAL AL DIA from line {idx}: '{line}'")
                continue

            # Check if the line starts with a date
            if self.is_date(line):
                # Extract FECHA and DESCRIPCION
                match = re.match(r"^(\d{1,2}/\d{1,2}/\d{2,4})\s+(.*)", line)
                if match:
                    fecha = match.group(1)
                    descripcion = match.group(2)
                else:
                    st.warning(f"Could not parse FECHA and DESCRIPCION from line {idx}: '{line}'")
                    continue

                # Initialize fields
                referencia = ""
                debitos = ""

                # Regex to extract DESCRIPCION, REFERENCIA, DEBITOS
                # This pattern assumes that REFERENCIA is either a number or '0'
                # and DEBITOS is a number with possible commas and dots
                transaction_pattern = r"^(?P<descripcion>.*?)\s+(?:(?P<referencia>\d+|0)\s+)?(?P<debitos>[\d.,]+)(?:\s+[\d.,]+)?$"
                trans_match = re.match(transaction_pattern, descripcion)

                if trans_match:
                    descripcion = trans_match.group('descripcion').strip()
                    referencia = trans_match.group('referencia').strip() if trans_match.group('referencia') else ""
                    debitos = trans_match.group('debitos').strip() if trans_match.group('debitos') else ""
                else:
                    st.warning(f"Could not parse transaction details from line {idx}: '{line}'")
                    continue

                # Assign fields without normalization to preserve original format
                parsed_entry = {
                    "FECHA": fecha,
                    "DESCRIPCION": descripcion,
                    "REFERENCIA": referencia,
                    "DEBITOS": debitos,
                    "CREDITOS": "",
                    "SALDO": ""
                }

                parsed_data.append(parsed_entry)
                st.write(f"Extracted Transaction: {parsed_entry}")
                continue

            # Skip other lines
            st.write(f"Skipping non-transaction line {idx}: '{line}'")

        # Optionally, verify if SALDO FINAL was captured
        if not saldo_final_present:
            st.warning("SALDO FINAL not found in the document.")

        return parsed_data

    def is_date(self, s: str) -> bool:
        """
        Checks if a string starts with a date pattern (e.g., dd/mm/yyyy or dd/mm/yy).
        """
        return bool(re.match(r"^\d{1,2}/\d{1,2}/\d{2,4}", s))
