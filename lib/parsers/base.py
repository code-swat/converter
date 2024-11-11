#rom lib.api.datalab import parse as datalab_parse
#rom lib.api.datalab_ocr import parse as datalab_ocr_parse
from lib.api.file import parse as file_parse
#from lib.api.file_tables import parse as file_tables_parse
#from lib.api.file_ocr import parse as file_ocr_parse
#rom lib.api.llamaparse import parse as llama_parse

from lib.parsers.bbva import BBVAParser
from lib.parsers.bpn import BPNParser
from lib.parsers.comafi import ComafiParser
from lib.parsers.credicoop import CredicoopParser
from lib.parsers.galicia import GaliciaParser
from lib.parsers.hsbc import HSBCParser
from lib.parsers.icbc import ICBCParser
from lib.parsers.macro import MacroParser
from lib.parsers.nacion import NacionParser
from lib.parsers.patagonia import PatagoniaParser
from lib.parsers.roela import RoelaParser
from lib.parsers.santander import SantanderParser
from lib.parsers.supervielle import SupervielleParser

parser_map = {
    "BBVA": (BBVAParser, file_parse, "✅"),
    "BPN": (BPNParser, file_parse, "✅"),
    "Comafi": (ComafiParser, file_parse, "❌"),
    "Credicoop": (CredicoopParser, file_parse, "❌"),
    "Galicia": (GaliciaParser, file_parse, "✅"),
    "HSBC": (HSBCParser, file_parse, "✅"),
    "ICBC": (ICBCParser, file_parse, "❌"),
    "Macro": (MacroParser, file_parse, "❌"),
    "Nación": (NacionParser, file_parse, "✅"),
    "Patagonia": (PatagoniaParser, file_parse, "❌"),
    "Roela": (RoelaParser, file_parse, "✅"),
    "Santander": (SantanderParser, file_parse, "✅"),
    "Supervielle": (SupervielleParser, file_parse, "✅")
}

class BankParser:
    @staticmethod
    def get_parser(bank_name: str):
        if bank_name in parser_map:
            return parser_map[bank_name][0]()
        else:
            raise ValueError(f"No parser found for bank: {bank_name}")

    @staticmethod
    def get_parser_api(bank_name: str):
        if bank_name in parser_map:
            return parser_map[bank_name][1]
        else:
            raise ValueError(f"No parser API found for bank: {bank_name}")
    
    @staticmethod
    def get_parser_status(bank_name: str):
        if bank_name in parser_map:
            return parser_map[bank_name][2]
        else:
            raise ValueError(f"No parser status found for bank: {bank_name}")

    @staticmethod
    def bank_names():
        return list(parser_map.keys())
