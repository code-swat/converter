from lib.parsers.galicia import GaliciaParser
from lib.parsers.bbva import BBVAParser
from lib.parsers.patagonia import PatagoniaParser

parser_map = {
    "Galicia": GaliciaParser,
    "BBVA": BBVAParser,
    "Patagonia": PatagoniaParser
}

class BankParser:
    @staticmethod
    def get_parser(bank_name: str):
        if bank_name in parser_map:
            return parser_map[bank_name]()
        else:
            raise ValueError(f"No parser found for bank: {bank_name}")

    @staticmethod
    def bank_names():
        return list(parser_map.keys())
