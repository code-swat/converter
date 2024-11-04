from lib.parsers.credicoop import CredicoopParser
from lib.parsers.galicia import GaliciaParser
from lib.parsers.bbva import BBVAParser
from lib.parsers.patagonia import PatagoniaParser
from lib.api.datalab import recognize_tables as datalab_recognize_tables
from lib.api.file import recognize_tables as file_recognize_tables

parser_map = {
    "Galicia": GaliciaParser,
    "BBVA": BBVAParser,
    "Patagonia": PatagoniaParser,
    "Credicoop": CredicoopParser
}

parser_api_map = {
    "Galicia": file_recognize_tables,
    "Credicoop": file_recognize_tables
}

class BankParser:
    @staticmethod
    def get_parser(bank_name: str):
        if bank_name in parser_map:
            return parser_map[bank_name]()
        else:
            raise ValueError(f"No parser found for bank: {bank_name}")

    @staticmethod
    def get_parser_api(bank_name: str):
        if bank_name in parser_api_map:
            return parser_api_map[bank_name]
        else:
            raise ValueError(f"No parser API found for bank: {bank_name}")

    @staticmethod
    def bank_names():
        return list(parser_map.keys())
