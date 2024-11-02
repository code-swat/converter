from typing import Dict

class PatagoniaParser():
    def parse(self, tables_data: Dict) -> Dict:
        parsed_data = {
            "bank": "Patagonia",
            "tables": tables_data
        }
        return parsed_data
