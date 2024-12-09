from typing import List, Dict, Tuple
import re

def convert_to_canonical_format(data: Dict) -> Dict:
    canonical_rows = []

    for row in data:
        saldo = row["Saldo"].replace('-', '') if row["Saldo"].endswith('-') else row["Saldo"]
        saldo = f'-{saldo}' if row["Saldo"].endswith('-') else saldo

        canonical_row = {
            "FECHA": row["Fecha"],
            "DETALLE": row["Conceptos"],
            "REFERENCIA": row["Referencias"],
            "DEBITOS": float(row["Débitos"].replace('.', '').replace(',', '.')) if row["Débitos"] else "", 
            "CREDITOS": float(row["Créditos"].replace('.', '').replace(',', '.')) if row["Créditos"] else "",
            "SALDO": float(saldo.replace('.', '').replace(',', '.')) if saldo else ""
        }

        canonical_rows.append(canonical_row)

    return canonical_rows

class ComafiParser:
    def __init__(self):
        # Configurable offsets (in characters)
        self.offset_fecha_start = -1
        self.offset_fecha_end = 0

        self.offset_conceptos_start = 0
        self.offset_conceptos_end = -1

        self.offset_referencias_start = 0
        self.offset_referencias_end = -8

        self.offset_debitos_start = -6
        self.offset_debitos_end = 1

        self.offset_creditos_start = -6
        self.offset_creditos_end = 1

        self.offset_saldo_start = -9
        self.offset_saldo_end = 2

    def parse(self, data: List[str]) -> List[List[Dict[str, str]]]:
        transactions_per_account = []
        current_account_transactions = []
        in_movements_section = False
        balance = None

        for page in data:
            lines = page.split('\n')
            headers_found = False
            header_positions = {}
            for line in lines:
                line_strip = line.strip()

                # Start processing section
                if not in_movements_section:
                    if "DETALLE DE MOVIMIENTOS" in line_strip:
                        in_movements_section = True
                    continue

                # Detect end of section
                if re.match(r'Saldo al:\s*\d{2}/\d{2}/\d{4}', line_strip):
                    saldo_al_data = self.extract_saldo_al(line_strip)
                    if saldo_al_data:
                        current_account_transactions.append(saldo_al_data)
                        transactions_per_account.append(convert_to_canonical_format(current_account_transactions))
                        current_account_transactions = []
                        balance = None
                        in_movements_section = False
                    continue

                # Identify header line
                if not headers_found and self.is_header_line(line_strip):
                    header_positions = self.get_headers_positions(line)
                    headers_found = True
                    continue

                if not headers_found:
                    continue

                # Skip "Transporte" sections and capture currency formatted number
                if re.match(r'Transporte\s+([\d\.]+,[\d]{2})', line_strip):
                    continue

                if not line_strip:
                    continue

                # Process transaction lines
                transaction_match = re.match(r'^(\d{2}/\d{2}/\d{2,4})\s+(.*)', line_strip)
                if transaction_match:
                    fecha = self.extract_fecha(line, header_positions)
                    conceptos, referencias = self.extract_conceptos_referencias(line, header_positions)
                    debitos = self.extract_debitos(line, header_positions)
                    creditos = self.extract_creditos(line, header_positions)
                    saldo = self.extract_saldo(line, header_positions)

                    if "Saldo Anterior" in conceptos:
                        saldo_anterior = saldo
                        if current_account_transactions:
                            transactions_per_account.append(convert_to_canonical_format(current_account_transactions))
                            current_account_transactions = []
                        current_account_transactions.append({
                            "Fecha": "",
                            "Conceptos": "Saldo Anterior",
                            "Referencias": "",
                            "Débitos": "",
                            "Créditos": "",
                            "Saldo": saldo_anterior
                        })
                        balance = self.parse_amount(saldo_anterior)
                        continue

                    transaction = {
                        "Fecha": fecha,
                        "Conceptos": conceptos,
                        "Referencias": referencias,
                        "Débitos": debitos,
                        "Créditos": creditos,
                        "Saldo": saldo
                    }

                    # Balance calculation and Saldo field updating
                    debitos_val = self.parse_amount(debitos)
                    creditos_val = self.parse_amount(creditos)
                    saldo_val = self.parse_amount(saldo) if saldo else None

                    if balance is not None:
                        balance -= debitos_val
                        balance += creditos_val
                        if saldo:
                            if abs(balance - saldo_val) > 0.01:
                                raise Exception(f"Balance mismatch at date {transaction['Fecha']}: calculated balance {balance}, reported balance {saldo_val}")
                        else:
                            transaction['Saldo'] = self.format_amount(balance)
                    else:
                        balance = saldo_val if saldo_val is not None else creditos_val - debitos_val
                        if not saldo:
                            transaction['Saldo'] = self.format_amount(balance)

                    current_account_transactions.append(transaction)
                    continue

                # Check for continuation line (no date at start, but has referencias or amounts)
                if headers_found and current_account_transactions:
                    referencias = line[header_positions['Referencias'][0] + self.offset_referencias_start:
                                 header_positions['Débitos'][0] + self.offset_referencias_end].strip()
                    debitos = self.extract_debitos(line, header_positions)
                    creditos = self.extract_creditos(line, header_positions)
                    saldo = self.extract_saldo(line, header_positions)

                    # If we found any data, append it to the previous transaction
                    if referencias or debitos or creditos or saldo:
                        prev_transaction = current_account_transactions[-1]
                        if referencias:
                            prev_transaction['Referencias'] = (prev_transaction['Referencias'] + '\n' + referencias).strip()
                        if debitos:
                            prev_transaction['Débitos'] = debitos
                        if creditos:
                            prev_transaction['Créditos'] = creditos
                        if saldo:
                            prev_transaction['Saldo'] = saldo

                        # Update balance calculation
                        debitos_val = self.parse_amount(debitos)
                        creditos_val = self.parse_amount(creditos)
                        saldo_val = self.parse_amount(saldo) if saldo else None

                        if balance is not None:
                            balance -= debitos_val
                            balance += creditos_val
                            if saldo:
                                if abs(balance - saldo_val) > 0.01:
                                    raise Exception(f"Balance mismatch at date {prev_transaction['Fecha']}: calculated balance {balance}, reported balance {saldo_val}")
                            else:
                                prev_transaction['Saldo'] = self.format_amount(balance)
                        else:
                            balance = saldo_val if saldo_val is not None else creditos_val - debitos_val
                            if not saldo:
                                prev_transaction['Saldo'] = self.format_amount(balance)
                    continue

        if current_account_transactions:
            transactions_per_account.append(convert_to_canonical_format(current_account_transactions))

        return transactions_per_account

    def is_header_line(self, line: str) -> bool:
        headers = ["Fecha", "Conceptos", "Referencias", "Débitos", "Créditos", "Saldo"]
        return all(header in line for header in headers)

    def get_headers_positions(self, header_line: str) -> Dict[str, Tuple[int, int]]:
        headers = ["Fecha", "Conceptos", "Referencias", "Débitos", "Créditos", "Saldo"]
        positions = {}
        for header in headers:
            match = re.search(r'\b' + re.escape(header) + r'\b', header_line)
            if match:
                positions[header] = (match.start(), match.end())
            else:
                raise Exception(f"Header '{header}' not found.")
        return positions

    def extract_fecha(self, line: str, header_positions: Dict[str, Tuple[int, int]]) -> str:
        start = header_positions['Fecha'][0] + self.offset_fecha_start
        end = header_positions['Conceptos'][0] + self.offset_fecha_end
        return line[start:end].strip()

    def extract_conceptos_referencias(self, line: str, header_positions: Dict[str, Tuple[int, int]]) -> Tuple[str, str]:
        start = header_positions['Conceptos'][0] + self.offset_conceptos_start
        end = header_positions['Referencias'][0] + self.offset_conceptos_end
        conceptos = line[start:end].strip()

        referencias = line[header_positions['Referencias'][0] + self.offset_referencias_start:
                               header_positions['Débitos'][0] + self.offset_referencias_end].strip()
        return conceptos, referencias

    def extract_debitos(self, line: str, header_positions: Dict[str, Tuple[int, int]]) -> str:
        start = header_positions['Débitos'][0] + self.offset_debitos_start
        end = header_positions['Débitos'][1] + self.offset_debitos_end
        return line[start:end].strip()

    def extract_creditos(self, line: str, header_positions: Dict[str, Tuple[int, int]]) -> str:
        start = header_positions['Créditos'][0] + self.offset_creditos_start
        end = header_positions['Créditos'][1] + self.offset_creditos_end
        return line[start:end].strip()

    def extract_saldo(self, line: str, header_positions: Dict[str, Tuple[int, int]]) -> str:
        start = header_positions['Saldo'][0] + self.offset_saldo_start
        end = header_positions['Saldo'][1] + self.offset_saldo_end
        return line[start:end].strip()

    def extract_saldo_anterior(self, text: str) -> Dict[str, str]:
        match = re.search(r'Saldo Anterior\s*([\d\.,]+)', text)
        if match:
            saldo = match.group(1)
            return {
                "Fecha": "",
                "Conceptos": "Saldo Anterior",
                "Referencias": "",
                "Débitos": "",
                "Créditos": "",
                "Saldo": saldo
            }
        return {}

    def extract_saldo_al(self, text: str) -> Dict[str, str]:
        match = re.search(r'Saldo al:\s*(\d{2}/\d{2}/\d{4})\s*([\d\.,]+)', text)
        if match:
            fecha = self.format_date(match.group(1))
            saldo = match.group(2)
            return {
                "Fecha": fecha,
                "Conceptos": "Saldo",
                "Referencias": "",
                "Débitos": "",
                "Créditos": "",
                "Saldo": saldo
            }
        return {}

    def parse_amount(self, amount_str: str) -> float:
        if not amount_str:
            return 0.0
        amount_str = amount_str.replace('.', '').replace(',', '.')
        amount_sign = 1
        if amount_str.endswith('-'):
            amount_sign = -1
            amount_str = amount_str[:-1]
        try:
            return amount_sign * float(amount_str)
        except ValueError:
            raise Exception(f"Unable to parse amount: '{amount_str}'")

    def format_amount(self, amount: float) -> str:
        return f"{amount:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

    def format_date(self, date_str: str) -> str:
        day, month, year = date_str.split('/')
        return f"{day}/{month}/{year[-2:]}"


sample_input_data = [
  "Los depósitos en pesos y en moneda extranjera cuentan con la garantía de hasta $ 1.500.000.- En las operaciones a nombre de dos ó más personas, la garantía se prorrateará entre sus titulares.  En ningún caso, el total de la garantía por\npersona y por depósito podrá exceder de $1.500.000, cualquiera sea el número de cuentas y/o depósitos. Ley 24.485, Decreto 540/95 y modificatorios y Com. \"A\" 2337 y sus modificatorias y complementarias. Se encuentran excluidos los \ncaptados a tasas superiores a la de referencia conforme a los límites establecidos por el Banco Central, los adquiridos por endoso y  los efectuados por personas vinculadas a la entidad financiera. \n\"Se ruega formular por escrito o personalmente  las  observaciones  a  este  extracto en  la  sucursal  de radicación  de  la  cuenta,  dentro  de  los 60 días  corridos  de  vencido  el  período.  En  caso  contrario se presumirá conformidad \nEl Impuesto al Valor Agregado discriminado no podrá ser computado como crédito fiscal si su condición frente a este impuesto es distinta a la de Responsable Inscripto.\n  (Circular OPASi 2 BCRA).\"\n                                                     Comafi Empresas Classic                       \n                                                                                            RESUMEN DE OPERACIONES                  \n                                                                                            ENERO - 2023                            \n                                                                                            Emision : Mensual                       \n                   81.477 - 1/2       - 12                                                                                          \n                  SERVICIOS Y SOLUCIONES INT SA                                                    Hoja:1/2                         \n                  Avenida Acceso Sur 4389                                                          Secuencia : 16                   \n                                                                                                   Código:E                         \n                  5507       Lujan De Cuyo                                                         CUIT 30710922973                 \n                  Mendoza                               Suc:171                                                                     \n001710000601\n  __________________________________________________________________________________________________________________________________\n  NOTICIAS                                                                                                                          \n  Te recordamos que cuando la contratación de un servicio, incluídos los servicios públicos                                         \n  domiciliarios, haya sido realizada en forma telefónica, electrónica o similar, podrá ser rescindida                               \n  a elección del consumidor o usuario mediante el mismo medio utilizado en la contratación. La empresa                              \n  receptora del pedido de rescisión del servicio deberá enviar sin cargo al domicilio del consumidor                                \n  o usuario una constancia fehaciente dentro de las SETENTA Y DOS (72) horas posteriores a la                                       \n  recepción del pedido de rescisión (Ley 26.361 - Art. 10° ter).                                                                    \n  El titular de los datos personales tiene la facultad de ejercer el derecho de acceso a los mismos en                              \n  forma gratuita a intervalos no inferiores a seis meses, salvo que se acredite un interés legítimo al                              \n  efecto conforme lo establecido en el artículo 14, inciso 3 de la Ley Nº25.326. La DIRECCION                                       \n  NACIONAL DE PROTECCION DE DATOS PERSONALES, Órgano de Control de la Ley Nº25.326, tiene la                                        \n  atribución de atender las denuncias y reclamos que se interpongan con relación al incumplimiento                                  \n  de las normas sobre protección de datos personales. El titular podrá en cualquier momento solicitar                               \n  el retiro o bloqueo de su nombre de los bancos de datos y/o el responsable o usuario que proveyó la                               \n  información.                                                                                                                      \n  A los efectos del debido cumplimiento a la Resol. 52/2012 de la Unidad de Información Financiera                                  \n  respecto a la identificación de las Personas Expuestas Políticamente (PEPS), te solicitamos                                       \n  tengas a bien acercarte a tu sucursal en caso de que seas o hayas sido funcionario/s público tanto                                \n  nacional como extranjero con la finalidad de explicarte la normativa vigente y cumplimentar los                                   \n  pasos correspondientes.                                                                                                           \n  Podés consultar el \"Régimen de Transparencia\" elaborado por el Banco Central sobre la base de la                                  \n  información proporcionada por los sujetos obligados a fin de comparar los costos, características                                 \n  y requisitos de los productos y servicios financieros, ingresando a                                                               \n  http://www.bcra.gob.ar/BCRAyVos/Regimen_de_transparencia.asp                                                                      \n  IMPORTANTE: Tené presente que si efectuas transacciones en cajeros automáticos de otras redes                                     \n  distintas de Banelco en el país, las mismas, independientemente de las comisiones que te cobremos                                 \n  por su uso, podrían estar alcanzadas por un costo extra que genera y te cobra el administrador de                                 \n  dicha red de manera directa realizando un débito en tu cuenta. Este costo te lo informará                                         \n  previamente el cajero automático antes de confirmar la transacción para que puedas decidir                                        \n  realizarla o no. Esos costos no son cobrados por Banco Comafi ni tiene injerencia alguna en los                                   \n  mismos. Recordá que tenés a disposición la red Banelco y Link para realizar las operaciones sin                                   \n  costo adicional al que percibe el Banco.                                                                                          \n  Te informamos que conforme las reglamentaciones de los Mercados y Resolución de la Comisión                                       \n  Nacional de Valores (CNV) 731/2018 la documentación de respaldo de cada operación se encuentra a                                  \n  tu disposición.                                                                                                                   \n  Comafi Token Empresas y Código SMS son los medios que deben utilizar todos los autorizantes                                       \n  de eBanking Empresas para aprobar las operaciones realizadas en dicho canal. Comafi Token                                         \n  Empresas está disponible en 2 soluciones: para celulares y computadoras. Para más información                                     \n  sobre adhesiones y uso, ingresá a www.comafi.com.ar o contactate con nuestro Centro de Atención                                   \n  a Empresas.                                                                                                                       \n  Para realizar consultas, denunciar delitos informáticos o anunciar alguna situación en particular,                                \n  podés comunicarte con nuestro Centro de Atención a Empresas telefónicamente al 0810-122-6622                                      \n  de lunes a viernes en el horario de 9 a 18hs o vía mail a comafiempresas@comafi.com.ar.                                           \n  Te informamos que la Oficina de Defensa al Consumidor en Lujan de Cuyo atiende en los siguientes                                  \n  teléfonos: (0261) 4984226                                                                                                         \n",
  "Los depósitos en pesos y en moneda extranjera cuentan con la garantía de hasta $ 1.500.000.- En las operaciones a nombre de dos ó más personas, la garantía se prorrateará entre sus titulares.  En ningún caso, el total de la garantía por\npersona y por depósito podrá exceder de $1.500.000, cualquiera sea el número de cuentas y/o depósitos. Ley 24.485, Decreto 540/95 y modificatorios y Com. \"A\" 2337 y sus modificatorias y complementarias. Se encuentran excluidos los \ncaptados a tasas superiores a la de referencia conforme a los límites establecidos por el Banco Central, los adquiridos por endoso y  los efectuados por personas vinculadas a la entidad financiera. \n\"Se ruega formular por escrito o personalmente  las  observaciones  a  este  extracto en  la  sucursal  de radicación  de  la  cuenta,  dentro  de  los 60 días  corridos  de  vencido  el  período.  En  caso  contrario se presumirá conformidad \nEl Impuesto al Valor Agregado discriminado no podrá ser computado como crédito fiscal si su condición frente a este impuesto es distinta a la de Responsable Inscripto.\n  (Circular OPASi 2 BCRA).\"\n  COMAFI EMPRESAS CLASSIC              Nro 0889226       Sucursal: Lujan De Cuyo - Mendoza            .                             \n  ----------------------------------------------------------------------------------------------------------------------------------\n  TITULAR                                                       CUIT                                     SITUACIÓN IMPOSITIVA       \n  ----------------------------------------------------------------------------------------------------------------------------------\n    SERVICIOS Y SOLUCIONES INT SA                               30-71092297-3                            Responsable Inscripto      \n  ----------------------------------------------------------------------------------------------------------------------------------\n  Productos COMAFI EMPRESAS CLASSIC         Número de Cuenta/Tarjeta   Moneda      Límite de Crédito                   Saldo        \n  ----------------------------------------------------------------------------------------------------------------------------------\n  Cuenta Corriente Bancaria                   1710-00060-1             Pesos                 0,00                     2.239.979,46  \n  Cuenta Corriente Especial                   1711-00233-0             Pesos                 0,00                             0,00  \n  Cuenta Corriente Especial                   1711-00234-7             Dolares               0,00                             0,00  \n                                                                              Total Pesos:                            2.239.979,46  \n  COMAFI EMPRESAS CLASSIC           CUENTA CORRIENTE BANCARIA EN PESOS                                .                             \n    Número 1710-00060-1                             CBU: 2990171317100006010002                                                     \n  ----------------------------------------------------------------------------------------------------------------------------------\n  DETALLE DE MOVIMIENTOS                                                                                                            \n  ----------------------------------------------------------------------------------------------------------------------------------\n   Fecha   Conceptos                          Referencias                                Débitos       Créditos              Saldo  \n  31/12/22                                                       Saldo Anterior                                        2.246.170,50 \n  03/01/23 Impuesto a los debitos - tasa gene 0012745                                        0,89                                   \n  03/01/23 Impuesto a los debitos - tasa gene 0012745                                        6,25                                   \n  03/01/23 Impuesto a los debitos - tasa gene 0012745                                       29,78                                   \n  03/01/23 Percepcion IVA RG 2408             0012745                                      148,89                                   \n  03/01/23 IVA - Alicuota General             0012745                                    1.042,23                                   \n  03/01/23 Comisión Mantenimiento Servicio Cu 0012745                                    4.963,00                      2.239.979,46 \n                                                                  Saldo al: 31/01/2023                                 2.239.979,46 \n  ----------------------------------------------------------------------------------------------------------------------------------\n  IMPUESTOS DEBITADOS EN EL PERIODO        Cuenta Corriente Bancaria Nro. 1710-00060-1                                              \n  ----------------------------------------------------------------------------------------------------------------------------------\n                                                        Base Imponible  Alícuota       Debitado    Devoluciones          Neto       \n  Ley 25413 Sobre  Débitos  Tasa general                      6.154,12   0,600%           36,92            0,00           36,92     \n  TOTAL AL: 31/01/23                                                                      36,92            0,00           36,92 (1) \n  (1)Total Pago a Cuenta Artículo 13 - Anexo Decreto 380/1: al 31/01/23           $ 12,18                                           \n  El importe discriminado es a sólo efecto de dar cumplimiento con lo establecido por la RG(AFIP) 1788/2004, debiendo el titular    \n  de la cuenta realizar los cálculos que correspondan a fin de determinar el pago a cuenta que resulte computable.                  \n  COMAFI EMPRESAS CLASSIC           CUENTA CORRIENTE ESPECIAL EN PESOS                                .                             \n    NRO. 1711-00233-0                               CBU: 2990171317110023300017                                                     \n  ----------------------------------------------------------------------------------------------------------------------------------\n  DETALLE DE MOVIMIENTOS                                                                                                            \n  ----------------------------------------------------------------------------------------------------------------------------------\n   Fecha   Conceptos                          Referencias                                Débitos       Créditos              Saldo  \n  31/12/22                                                       Saldo Anterior                                                0,00 \n                                                           SIN MOVIMIENTOS                                                          \n                                                                  Saldo al: 31/01/2023                                         0,00 \n  COMAFI EMPRESAS CLASSIC           CUENTA CORRIENTE ESPECIAL EN DOLARES                              .                             \n    NRO. 1711-00234-7                               CBU: 2990171317110023470219                                                     \n",
  "Los depósitos en pesos y en moneda extranjera cuentan con la garantía de hasta $ 1.500.000.- En las operaciones a nombre de dos ó más personas, la garantía se prorrateará entre sus titulares.  En ningún caso, el total de la garantía por\npersona y por depósito podrá exceder de $1.500.000, cualquiera sea el número de cuentas y/o depósitos. Ley 24.485, Decreto 540/95 y modificatorios y Com. \"A\" 2337 y sus modificatorias y complementarias. Se encuentran excluidos los \ncaptados a tasas superiores a la de referencia conforme a los límites establecidos por el Banco Central, los adquiridos por endoso y  los efectuados por personas vinculadas a la entidad financiera. \n\"Se ruega formular por escrito o personalmente  las  observaciones  a  este  extracto en  la  sucursal  de radicación  de  la  cuenta,  dentro  de  los 60 días  corridos  de  vencido  el  período.  En  caso  contrario se presumirá conformidad \nEl Impuesto al Valor Agregado discriminado no podrá ser computado como crédito fiscal si su condición frente a este impuesto es distinta a la de Responsable Inscripto.\n  (Circular OPASi 2 BCRA).\"\n   81.477 - 2/2       - 12                                                SERVICIOS Y SOLUCIONES INT SA                             \n                                                                          Hoja:2/2                                                  \n  ----------------------------------------------------------------------------------------------------------------------------------\n  DETALLE DE MOVIMIENTOS                                                                                                            \n  ----------------------------------------------------------------------------------------------------------------------------------\n   Fecha   Conceptos                          Referencias                                Débitos       Créditos              Saldo  \n  31/12/22                                                       Saldo Anterior                                                0,00 \n                                                           SIN MOVIMIENTOS                                                          \n                                                                  Saldo al: 31/01/2023                                         0,00 \n  ----------------------------------------------------------------------------------------------------------------------------------\n"
]


expected_data = [
    {
        "Fecha": "31/12/22",
        "Conceptos": "Saldo Anterior",
        "Referencias": "",
        "Débitos": "",
        "Créditos": "",
        "Saldo": "2.246.170,50"
    },
    {
        "Fecha": "03/01/23",
        "Conceptos": "Impuesto a los debitos - tasa gene",
        "Referencias": "0012745",
        "Débitos": "0,89",
        "Créditos": "",
        "Saldo": ""
    },
    {
        "Fecha": "03/01/23",
        "Conceptos": "Impuesto a los debitos - tasa gene",
        "Referencias": "0012745",
        "Débitos": "6,25",
        "Créditos": "",
        "Saldo": ""
    },
    {
        "Fecha": "03/01/23",
        "Conceptos": "Impuesto a los debitos - tasa gene",
        "Referencias": "0012745",
        "Débitos": "29,78",
        "Créditos": "",
        "Saldo": ""
    },
    {
        "Fecha": "03/01/23",
        "Conceptos": "Percepcion IVA RG 2408",
        "Referencias": "0012745",
        "Débitos": "148,89",
        "Créditos": "",
        "Saldo": ""
    },
    {
        "Fecha": "03/01/23",
        "Conceptos": "IVA - Alicuota General",
        "Referencias": "0012745",
        "Débitos": "1.042,23",
        "Créditos": "",
        "Saldo": ""
    },
    {
        "Fecha": "03/01/23",
        "Conceptos": "Comisión Mantenimiento Servicio Cu",
        "Referencias": "0012745",
        "Débitos": "4.963,00",
        "Créditos": "",
        "Saldo": "2.239.979,46"
    },
    {
        "Fecha": "31/01/23",
        "Conceptos": "Saldo",
        "Referencias": "",
        "Débitos": "",
        "Créditos": "",
        "Saldo": "2.239.979,46"
    }
]