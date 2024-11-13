import re
import streamlit as st
from typing import Dict, List

def convert_to_canonical_format(data: Dict) -> Dict:
    canonical_rows = []

    for row in data:
        canonical_row = {
            "FECHA": row["Fecha"],
            "DETALLE": row["Movimiento"],
            "REFERENCIA": row["Comprobante"],
            "DEBITOS": float(row["Débito"].replace('.', '').replace(',', '.')) if row["Débito"] else "", 
            "CREDITOS": float(row["Crédito"].replace('.', '').replace(',', '.')) if row["Crédito"] else "",
            "SALDO": float(row["Saldo en cuenta"].replace('.', '').replace(',', '.')) if row["Saldo en cuenta"] else ""
        }

        canonical_rows.append(canonical_row)

    return canonical_rows

class SantanderParser:
    def parse(self, data: List[str]) -> List[List[Dict[str, str]]]:
        data_str = self.clean_pages(data)
        lines = data_str.split('\n')

        transactions = []
        current_date = ''
        current_comprobante = ''
        current_movimiento = []
        debito = ''
        credito = ''
        saldo_en_cuenta = ''
        previous_saldo = None
        i = 0
        n = len(lines)
        
        # Find the start index: first date line followed by "Saldo Inicial"
        start_index = -1
        for idx in range(n-1):
            if re.match(r'^\d{2}/\d{2}/\d{2}$', lines[idx].strip()) and 'Saldo Inicial' in lines[idx+1]:
                start_index = idx
                break
        if start_index == -1:
            return []
        i = start_index
        
        while i < n:
            line = lines[i].strip()
            
            # End processing when "Saldo total" is encountered
            if 'Saldo total' in line and 'pesos' in lines[i+1]:
                break
            
            # Check for date and comprobante on the same line
            date_comprobante_match = re.match(r'^(\d{2}/\d{2}/\d{2})\s+(\d+)$', line)
            if date_comprobante_match:
                current_date = date_comprobante_match.group(1)
                current_comprobante = date_comprobante_match.group(2)
                i += 1
                continue
            
            # Check for standalone date line
            date_match = re.match(r'^(\d{2}/\d{2}/\d{2})$', line)
            if date_match:
                current_date = date_match.group(1)
                current_comprobante = ''
                i += 1
                continue
            
            # Check for "Saldo Inicial"
            if 'Saldo Inicial' in line:
                movimiento = 'Saldo Inicial'
                comprobante = ''
                debito = ''
                credito = ''
                # Next line should have 'pesos' and amount
                if i+1 < n and 'pesos' in lines[i+1]:
                    saldo_en_cuenta = self.format_amount(self.parse_amount(lines[i+1]))
                    transactions.append({
                        'Fecha': current_date,
                        'Comprobante': comprobante,
                        'Movimiento': movimiento,
                        'Débito': debito,
                        'Crédito': credito,
                        'Saldo en cuenta': saldo_en_cuenta
                    })
                    previous_saldo = self.parse_amount(lines[i+1])
                    i += 2
                    continue
            
            # Check for comprobante line
            comprobante_match = re.match(r'^(\d+)$', line)
            if comprobante_match and not current_comprobante:
                current_comprobante = comprobante_match.group(1)
                i += 1
                continue
            
            # Collect Movimiento lines
            movimiento_lines = []
            while i < n and not lines[i].strip().startswith('pesos') and not re.match(r'^\d{2}/\d{2}/\d{2}$', lines[i].strip()) and not re.match(r'^\d+$', lines[i].strip()):
                movimiento_lines.append(lines[i].strip())
                i += 1
            movimiento = '\n'.join(movimiento_lines).strip()
            
            # Collect Débito/Credito and Saldo en cuenta
            debito_credito = ''
            saldo = ''
            if i < n and 'pesos' in lines[i].strip():
                debito_credito = lines[i].strip()
                i += 1
            if i < n and 'pesos' in lines[i].strip():
                saldo = lines[i].strip()
                i += 1
            
            debito_amount = self.parse_amount(debito_credito) if debito_credito else None
            saldo_amount = self.parse_amount(saldo) if saldo else None
            
            if previous_saldo is not None and saldo_amount is not None and debito_amount is not None:
                if abs(previous_saldo - debito_amount - saldo_amount) < 0.01:
                    debito = self.format_amount(debito_amount)
                elif abs(previous_saldo + debito_amount - saldo_amount) < 0.01:
                    credito = self.format_amount(debito_amount)
            saldo_en_cuenta = self.format_amount(saldo_amount) if saldo_amount is not None else ''
            previous_saldo = saldo_amount
            
            transactions.append({
                'Fecha': current_date,
                'Comprobante': current_comprobante,
                'Movimiento': movimiento,
                'Débito': debito,
                'Crédito': credito,
                'Saldo en cuenta': saldo_en_cuenta
            })
            
            # Reset comprobante after use
            current_comprobante = ''
            debito = ''
            credito = ''
        
        return [convert_to_canonical_format(transactions)]

    def parse_amount(self, amount_str):
        amount_str = amount_str.replace(' ', '').replace('pesos', '').replace('menos', '-')
        amount_str = amount_str.replace('.', '').replace(',', '.')
        try:
            return float(amount_str)
        except ValueError:
            return None

    def format_amount(self, amount):
        if amount is None:
            return ''
        return "{:,.2f}".format(amount).replace(',', ' ').replace('.', ',').replace(' ', '.')
    
    def clean_pages(self, pages):
        last_header_regex = r'saldo en cuenta'
        cc_or_ca_regex = r'cuenta corriente n|caja de ahorro n'
        lines = []

        for page in pages:
            first_line = True
            skip_until_headers = False

            for line in page.split('\n'):
                if first_line and re.search(cc_or_ca_regex, line.lower()):
                    skip_until_headers = True
                    continue
                
                if skip_until_headers and re.search(last_header_regex, line.lower()):
                    skip_until_headers = False
                    continue
                
                if not skip_until_headers:
                    lines.append(line)

                first_line = False

        return '\n'.join(line for line in lines if line.strip())

sample_data = [
  "Resumen de cuenta\nLUIFRAN SOCIEDAD ANONIMA \n\n CUIT: 30-71547265\n-8\nRESPONSABLE INSCRIPTO\nAV GRAL SAN MARTIN 941 9 1\nM5500AAJ MENDOZA, MENDOZA\nO\nPeríodo\nEmisión mensual\nDesde: 30/12/23\nHasta:  31/01/24\nCuentas\nCuenta Corriente\nSaldo total en cuentas al 31/01/24*\npe\nsos \n346.083\n,\n23\n dólares 0,00\nBanco Santander Argentina S.A. es una sociedad anónima según la ley argentina, sito en Av. Juan de Garay 151 CABA (C1063ABB); CUIT 30-50000845-4; I.G.J. Nro. \ncorrelativo 800678. Ningún accionista mayoritario de capital extranjero responde por las operaciones del Banco, en exceso de su integración accionaria (Ley 25.738); \ntampoco lo hacen otras entidades que utilicen la marca Santander.\n* Salvo error u omisión\n* Salvo error u omisión\n",
  "Cuenta Corriente\nPeríodo\nEmisión mensual\nDesde: 30/12/23\nHasta:  31/01/24\nSaldo total en cuentas al 31/01/24 *\nTotal en pesos\n 346.083,23 Tota\nl \nen d\nólares \n0\n,0\n0\n* Salvo error u omisión\nMovimientos en pesos\nCuenta Corriente Nº 229-004113/7  CBU:  0720229420000000411372   Acuerdo:  pesos 38.000,00   Vencimiento:  30/04/24\nFecha\nComprobante\nMovimiento\nDébito\nCrédito\nSaldo en cuenta\n30/12/23\nSaldo Inicial \npesos 249.782,95\n02/01/24 22369248\nCompra con tarjeta de debito \nYpf hekar srl - tarj nro. 1301\npesos 20.000,00\npesos 229.782,95\n02/01/24\n33463649\nPago de tarjeta de credito visa \nPor deb:02/01/2024 part 000000000833463649\npesos 31.430,00\npesos 198.352,95\n02/01/24\nImpuesto ley 25.413 debito 0,6% \npesos 308,58\npesos 198.044,37\n08/01/24 20494844\nCompra con tarjeta de debito \nYpf aca mendoza - tarj nro. 1301\npesos 14.999,96\npesos 183.044,41\n08/01/24\n20272837\nDebito transf. online banking emp \n00720361005000023506ars\npesos 70.785,00\npesos 112.259,41\n08/01/24\nImpuesto ley 25.413 debito 0,6% \npesos 514,71\npesos 111.744,70\n09/01/24\nCobro de interes por descubierto \nDel 01/12/23 al 31/12/23\npesos 2.118,63\npesos 109.626,07\n09/01/24\nIva - reducido 10,5% \npesos 403,00\npesos 109.223,07\n09/01/24\nImpuesto de sellos \npesos 40,54\npesos 109.182,53\n09/01/24\nIntereses por descubierto excedido \nDel 01/12/23 al 31/12/23\npesos 1.719,49\npesos 107.463,04\n09/01/24\nImpuesto ley 25.413 debito 0,6% \npesos 25,69\npesos 107.437,35\n12/01/24 21915941\nCompra con tarjeta de debito \nParque combustible sa - tarj nro. 1301\npesos 20.000,00\npesos 87.437,35\n12/01/24\n550401\nReintegro carnicerias minoristas \nDevol consumo $ 37.219,40 13/12/2023\npesos 2.000,00\npesos 89.437,35\n12/01/24\nImpuesto ley 25.413 credito 0,6% \npesos 12,00\npesos 89.425,35\n12/01/24\nImpuesto ley 25.413 debito 0,6% \npesos 120,00\npesos 89.305,35\n15/01/24 14132927\nCompra con tarjeta de debito \nYpf allub hnos srl - tarj nro. 1301\npesos 20.000,00\npesos 69.305,35\n15/01/24\nImpuesto ley 25.413 debito 0,6% \npesos 120,00\npesos 69.185,35\n",
  "Cuenta Corriente Nº 229-004113/7  CBU:  0720229420000000411372   Acuerdo:  pesos 38.000,00   Vencimiento:  30/04/24\nFecha\nComprobante\nMovimiento\nDébito\nCrédito\nSaldo en cuenta\n16/01/24 270679\nDebito automatico \nAfip -30715472658\npesos 53.063,42\npesos 16.121,93\n16/01/24\nImpuesto ley 25.413 debito 0,6% \npesos 318,38\npesos 15.803,55\n18/01/24 17485849\nCompra con tarjeta de debito \nEstacion de servicio g - tarj nro. 1301\npesos 20.000,00\npesos menos 4.196,45\n18/01/24\nImpuesto ley 25.413 debito 0,6% \npesos 120,00\npesos menos 4.316,45\n23/01/24 12702132\nCompra con tarjeta de debito \nEstacion de servicio g - tarj nro. 1301\npesos 10.000,00\npesos menos 14.316,45\n23/01/24\nImpuesto ley 25.413 debito 0,6% \npesos 60,00\npesos menos 14.376,45\n26/01/24 16778361\nCompra con tarjeta de debito \nMerpago*litoenergia - tarj nro. 1301\npesos 20.000,00\npesos menos 34.376,45\n26/01/24\n8786775\nPago a proveedores recibido \nMh tgp gob. mendoza pago a pr 30999259169 03 8786775\npesos 1.420.366,07\npesos 1.385.989,62\n26/01/24\nImpuesto ley 25.413 debito 0,6% \npesos 120,00\npesos 1.385.869,62\n26/01/24\nImpuesto ley 25.413 credito 0,6% \npesos 8.522,20\npesos 1.377.347,42\n26/01/24\nRegimen de recaudacion sircreb c \nResponsable:30715472658 / 0,10% sobre $1.420.366,07\npesos 1.420,37\npesos 1.375.927,05\n29/01/24 1077073\nCompra con tarjeta de debito \nKadeem sa - tarj nro. 1301\npesos 16.600,00\npesos 1.359.327,05\n29/01/24\n15008547\nCompra con tarjeta de debito \nCarnes rizzo - tarj nro. 1301\npesos 31.992,40\npesos 1.327.334,65\n29/01/24\nImpuesto ley 25.413 debito 0,6% \npesos 300,07\npesos 1.327.034,58\n30/01/24\nComision por servicio de cuenta \npesos 23.625,00\npesos 1.303.409,58\n30/01/24\nIva 21% \npesos 4.961,25\npesos 1.298.448,33\n30/01/24\nIva percepcion rg 2408 \npesos 708,75\npesos 1.297.739,58\n30/01/24\nImpuesto ley 25.413 debito 0,6% \npesos 175,77\npesos 1.297.563,81\n31/01/24 571\nCheque debitado \npesos 339.000,00\npesos 958.563,81\n31/01/24\n572\nCheque debitado \npesos 339.000,00\npesos 619.563,81\n31/01/24\n4155386\nTransferencia realizada \nA querandi sa / factura - fac / 30707249303\npesos 69.060,75\npesos 550.503,06\n31/01/24\n4156053\nTransferencia realizada \nA sosa alonso matias patr / factura - fac / 20270620591\npesos 15.250,00\npesos 535.253,06\n31/01/24\n9448651\nDebito transf. online banking emp \nA luis javier caballero / factura - fac / 23183428489\npesos 172.000,00\npesos 363.253,06\n31/01/24\n11505503\nDebito transf. online banking emp \nA gestion medios sa / factura - fac / 30716073021\npesos 11.495,00\npesos 351.758,06\n31/01/24\nImpuesto ley 25.413 debito 0,6% \npesos 5.674,83\npesos 346.083,23\n",
  "Saldo total  \npesos 346.083,23\nMovimientos en dólares\nCuenta Corriente especial U$S Nº 229-004114/4  CBU:  0720229421000000411441\nFecha\nComprobante\nMovimiento\nDébito\nCrédito\nSaldo en cuenta\n30/12/23\nSaldo Inicial \ndólares 0,00\nNo tenés movimientos en dólares este período.\nSaldo total  \ndólares 0,00\nDetalle impositivo\nCuenta Corriente en pesos Nº 229-004113/7  CBU:  0720229420000000411372\nTipo de impuesto\nImporte\nTotales de retencion impuesto ley 25413 del 30-12-2023 al 31-01-2024\nTotal retencion impuesto ley 25413 por creditos\npesos 8.534,20\nTotal retencion impuesto ley 25413 por debitos\npesos 7.858,03\nImporte susceptible de ser computado contra otros tributos del 30-12-2023 al 31-01-2024\nPor retencion impuesto ley 25413 por creditos alicuota 33,00 %\npesos 2.816,29\nPor retencion impuesto ley 25413 por debitos alicuota 33,00 %\npesos 2.593,14\nTotal Retención Régimen de Recaudación SIRCREB \nen el período de emisión\npesos 1.420,37\nTasas de Acuerdos y Descubierto\nCuenta Corriente en pesos Nº 229-004113/7\nFecha\nTipo\nNúmero\nLímite\nVencimiento\nUtilizado \ndesde\nUtilizado \nhasta\nTNA\nTEA\nCFTEA\nInterés cobrado\n09/01/24\nComun\n-\npesos 38.000,00\n30/04/24\n01/12/23\n31/12/23\n185,00%\n458,75%\n458,75%\npesos 2.118,63\n09/01/24\nExcedido\n-\npesos -\n-\n01/12/23\n31/12/23\n195,00%\n509,13%\n509,13%\npesos 1.719,49\n",
  "Legales\nCuentas\nIntercambio de información\nSi te encontrás alcanzado por el estandar referido al intercambio de información de cuentas financieras desarrollado \npor la Organización para la Cooperación y el Desarrollado Económicos (OCDE), esta entidad bancaria deberá informar \ndicha situación a los organismos de contralor que la normativa vigente designe a tal efecto.\nGarantía de los depósitos\nLos depósitos en pesos y en moneda extranjera cuentan con la garantía de hasta $6.000.000. En las operaciones a \nnombre de dos o más personas, la garantía se prorrateará entre sus titulares. En ningún caso, el total de la garantía \npor persona y por depósito podrá exceder de $6.000.000, cualquiera sea el número de cuentas y/o depósitos. Ley \n24.485, Decreto N° 540/95 y modificatorios y Com. \"A\" 2337 y sus modificatorias y complementarias. Se encuentran \nexcluidos los captados a tasas superiores a la de referencia conforme a los límites establecidos por el Banco Central, \nlos adquiridos por endoso y los efectuados por personas vinculadas a la entidad financiera.\nAcuerdo de giro en descubierto\nSi tenes un Acuerdo de giro en descubierto la tasa máxima de interés a aplicar en el mes de Marzo de 2024, será: \n185,00%. Tasa Nominal Anual, 458,76% Tasa Efectiva Anual, CFTEA (persona jurídica) 458,76%, CFTEA (persona física) \n460,53%. Si en el mencionado mes el Banco autorizara giros en descubierto sin acuerdo previo o excesos en el monto \nacordado, la tasa máxima aplicable será 195,00% Tasa Nominal Anual, 509,14% Tasa Efectiva Anual, CFTEA (persona \njurídica) 509,14%, CFTEA (persona física) 510,91%.\nCFTEA: Costo Financiero Total Efectivo Anual.\nImpuestos al débito y crédito\nEl importe susceptible de ser computado contra otros tributos durante el período informado es el equivalente al \nporcentaje indicado en art. 13 de la Ley 25.413 por débitos y créditos aquí informados (Decreto 409/2018)\nCheques\nDepósito de cheques\nAviso  Importante:  La  disponibilidad  de  fondos  de  los  movimientos  de  cheques  24 hs.  se  efectiviza  a  partir  \nde  las  13 hs.  del  día siguiente  hábil  al  depósito.  Antes  de  ese  horario,  los  movimientos  del  extracto  con  \nestas  características  deben  considerarse  a confirmar.\nSolicitud de cheques físicos\nVas a poder solicitar los cheques físicos pagado en la sucursal, donde tengas radicada tu cuenta corriente, durante \nun plazo de 60 días corridos desde la fecha de pago. una vez transcurrido el plazo indicado, esta entidad podrá \nproceder a la destrucción de los mismos conservando únicamente sus reproducciones.\nECHEQs\nEn caso de que hayas librado cheques de pago diferido bajo la modalidad de ECHEQ (cheques generados por medios \nelectrónicos), te recordamos que podés consultar el detalle de los ECHEQ pendientes de pago a través de Online \nBanking ingresando a Cuentas / CC correspondiente / Echeq / Consulta de Echeq.\n",
  "Otros\nFondos Comunes de inversión\nLas inversiones en cuotas del fondo no constituyen depósitos en Banco Santander Argentina S.A. a los fines de la Ley \nde Entidades Financieras ni cuentan con ninguna de las garantías que tales depósitos a la vista o a plazo puedan \ngozar de acuerdo con la legislación y reglamentación aplicables en materia de depósitos en entidades financieras. \nAsimismo, Banco Santander Argentina S.A. se encuentra impedida por normas del Banco Central de la República \nArgentina de asumir, tácita o expresamente, compromiso alguno en cuanto al mantenimiento, en cualquier \nmomento, del valor del capital invertido, al rendimiento, al valor de rescate de las cuota partes o al otorgamiento de \nliquidez a tal fin.\nUnidad de Información Financiera\nLa Unidad de Información Financiera (UIF) en la Resolución vigente establece las medidas y procedimientos que debe \nobservar el Sector Financiero, incorporando nuevos requisitos  que deberán cumplir las Personas Jurídicas para \nidentificar al Beneficiario/a Final, a saber: , \" ..será considerado Beneficiario/a Final a la/s persona/s humana/s que \nposea/n como mínimo el diez por ciento (10 %) del capital o de los derechos de voto de una persona jurídica, un \nfideicomiso, un fondo de inversión, un patrimonio de afectación y/o de cualquier otra estructura jurídica; y/o a la/s \npersona/s humana/s que por otros medios ejerza/n el control final de las mismas .. Se entenderá como control final \nal ejercido, de manera directa o indirecta, por una o más personas humanas mediante una cadena de titularidad y/o \na través de cualquier otro medio de control y/o cuando, por circunstancias de hecho o derecho, la/s misma/s tenga/n \nla potestad de conformar por sí la voluntad social para la toma de las decisiones por parte del órgano de gobierno de \nla persona jurídica o estructura jurídica y/o para la designación y/o remoción de integrantes del órgano de \nadministración de las mismas. \".,El texto de la referida norma se encuentra disponible en www.argentina.gob.ar/uif \npudiendo ser consultados en Normativa / Comunicaciones y Normativa/ Resoluciones respectivamente.\n¿Tenés alguna consulta? \n Operá con seguridad\nLlamanos al 4341-3048 o desde el interior del país al \n0810-333-2552 de lunes a viernes de 9 a 18 hs (excepto \nferiados) o visitanos en nuestras sucursales. Ante la falta \nde respuesta o de disconformidad en la resolución de tus \nreclamos, contactate al Servicio de Atención al Usuario de \nServicios Financieros, cuyos datos se encuentran publicados \nen su sitio web.\n \nNo te dejes guiar telefónicamente en transacciones en \ncajeros automáticos ni mientras usás Online Banking o la \nApp Santander. No compartas por redes sociales, teléfono o \nemail tus claves personales. Nadie en nombre del banco te \nlas va a pedir.\nRecordá que contás con 30 días desde la fecha de recepción de este resumen para observar los conceptos \nque se incluyen en el mismo. Se considerará aceptado, en el caso de no registrarse objeciones en dicho \nlapso.\n"
]


expected_output = [
    {
        "Fecha": "30/12/23",
        "Comprobante": "",
        "Movimiento": "Saldo Inicial",
        "Débito": "",
        "Crédito": "",
        "Saldo en cuenta": "249.782,95"
    },
    {
        "Fecha": "02/01/24",
        "Comprobante": "22369248",
        "Movimiento": "Compra con tarjeta de debito\nYpf hekar srl - tarj nro. 1301",
        "Débito": "20.000,00",
        "Crédito": "",
        "Saldo en cuenta": "229.782,95"
    },
    {
        "Fecha": "02/01/24",
        "Comprobante": "33463649",
        "Movimiento": "Pago de tarjeta de credito visa\nPor deb:02/01/2024 part 000000000833463649",
        "Débito": "31.430,00",
        "Crédito": "",
        "Saldo en cuenta": "198.352,95"
    },
    {
        "Fecha": "02/01/24",
        "Comprobante": "",
        "Movimiento": "Impuesto ley 25.413 debito 0,6%",
        "Débito": "308,58",
        "Crédito": "",
        "Saldo en cuenta": "198.044,37"
    },
    {
        "Fecha": "08/01/24",
        "Comprobante": "20494844",
        "Movimiento": "Compra con tarjeta de debito\nYpf aca mendoza - tarj nro. 1301",
        "Débito": "14.999,96",
        "Crédito": "",
        "Saldo en cuenta": "183.044,41"
    }
]