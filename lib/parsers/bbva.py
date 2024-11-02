from typing import Dict

class BBVAParser():
    def parse(self, tables_data: Dict) -> Dict:
        parsed_data = {
            "bank": "BBVA",
            "tables": tables_data
        }
        return parsed_data
