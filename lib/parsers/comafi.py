import re
from typing import List, Dict
import streamlit as st

class ComafiParser:
    def parse(self, data: List[str]) -> List[Dict[str, str]]:
        transactions = []
        stop_processing = False
        saldo_carry = None

        # Regular expressions
        detalle_movimientos_regex = re.compile(r'DETALLE DE MOVIMIENTOS', re.IGNORECASE)
        date_regex = re.compile(r'^\d{2}/\d{2}/\d{2}')
        # Updated regex to capture both date and saldo, allowing variable spaces
        saldo_al_regex = re.compile(r'Saldo al:\s*(\d{2}/\d{2}/\d{4})\s+([\d\.,]+)', re.IGNORECASE)
        transporte_regex = re.compile(r'Transporte\s+[\d\.,]+', re.IGNORECASE)
        header_regex = re.compile(
            r'\bFecha\b.*\bConceptos\b.*\bReferencias\b.*\bDébitos\b.*\bCréditos\b.*\bSaldo\b',
            re.IGNORECASE
        )
        currency_regex = re.compile(r'[\d\.,]+')

        # Helper function to convert currency string to float
        def to_float(s):
            try:
                return float(s.replace('.', '').replace(',', '.'))
            except ValueError:
                st.error(f"Unable to convert currency string to float: {s}")
                return 0.0

        for page_index, page in enumerate(data):
            st.info(f"Processing page {page_index + 1}")
            lines = page.split('\n')
            i = 0

            while i < len(lines) and not stop_processing:
                line = lines[i]

                # Detect "DETALLE DE MOVIMIENTOS"
                if detalle_movimientos_regex.search(line):
                    st.info(f"Processing DETALLE DE MOVIMIENTOS at page {page_index + 1}, line {i + 1}")
                    i += 1  # Move to the next line after DETALLE DE MOVIMIENTOS

                    # Find header line
                    while i < len(lines):
                        header_line = lines[i]
                        if header_regex.search(header_line):
                            # Extract header positions
                            headers = ["Fecha", "Conceptos", "Referencias", "Débitos", "Créditos", "Saldo"]
                            headers_positions = {}
                            for header in headers:
                                match = re.search(r'\b' + re.escape(header) + r'\b', header_line)
                                if match:
                                    headers_positions[header] = match.start()
                                else:
                                    st.error(f"Header '{header}' not found at page {page_index + 1}, line {i + 1}.")
                                    headers_positions = {}
                                    break

                            if not headers_positions:
                                st.warning(f"Skipping DETALLE DE MOVIMIENTOS due to missing headers at page {page_index + 1}, line {i + 1}.")
                                i += 1
                                break  # Skip to next DETALLE

                            # Sort headers by their positions
                            sorted_headers = sorted(headers_positions.items(), key=lambda x: x[1])
                            field_boundaries = {}
                            for idx, (header, start_pos) in enumerate(sorted_headers):
                                if header == "Referencias":
                                    end_pos = start_pos + 35
                                elif header == "Créditos":
                                    end_pos = start_pos + len("Créditos") + 1
                                elif header == "Saldo":
                                    end_pos = field_boundaries["Créditos"][1] + 1
                                else:
                                    end_pos = sorted_headers[idx + 1][1] if idx + 1 < len(sorted_headers) else None

                                field_boundaries[header] = (start_pos, end_pos)

                            st.success(f"Headers detected with boundaries: {field_boundaries}")
                            i += 1  # Move to the line after headers
                            break
                        elif transporte_regex.search(header_line):
                            st.warning(f"Skipping Transporte section at page {page_index + 1}, line {i + 1}")
                            # Skip Transporte section
                            while i < len(lines) and not header_regex.search(lines[i]):
                                i += 1
                            break
                        else:
                            i += 1
                    else:
                        st.error(f"Header line not found after DETALLE DE MOVIMIENTOS at page {page_index + 1}.")
                        # Skip to next DETALLE
                        break

                    if not field_boundaries:
                        continue  # Skip processing transactions for this DETALLE

                    # Process transactions until "Saldo al" is found
                    while i < len(lines):
                        current_line = lines[i].strip()

                        # Stop if "Saldo al" is found
                        saldo_al_match = saldo_al_regex.search(current_line)
                        if saldo_al_match:
                            fecha_saldo = saldo_al_match.group(1)
                            final_saldo = saldo_al_match.group(2)
                            transaction = {
                                "Fecha": fecha_saldo,
                                "Conceptos": "Saldo",
                                "Referencias": "",
                                "Débitos": "",
                                "Créditos": "",
                                "Saldo": final_saldo
                            }
                            transactions.append(transaction)
                            st.info(f"Added final Saldo transaction: {transaction}")
                            i += 1  # Move past the Saldo al line
                            stop_processing = True
                            break  # Exit current DETALLE DE MOVIMIENTOS section

                        # Skip empty lines
                        if not current_line:
                            i += 1
                            continue

                        # Skip Transporte lines within transactions
                        if transporte_regex.search(current_line):
                            st.warning(f"Skipping Transporte transaction at page {page_index + 1}, line {i + 1}")
                            # Skip lines until next transaction or headers
                            while i < len(lines) and not date_regex.match(lines[i]):
                                i += 1
                            continue

                        # Detect transaction start with date
                        date_match = date_regex.match(current_line)
                        if date_match:
                            try:
                                fecha = date_match.group()
                                transaction = {
                                    "Fecha": fecha,
                                    "Conceptos": "",
                                    "Referencias": "",
                                    "Débitos": "",
                                    "Créditos": "",
                                    "Saldo": ""
                                }
                                st.info(f"Processing transaction starting at line {i + 1}: {fecha}")

                                # Extract fields based on field boundaries, ensure slicing is within line length
                                def get_field(line, start, end):
                                    if end and end <= len(line):
                                        return line[start:end].strip()
                                    elif start < len(line):
                                        return line[start:].strip()
                                    else:
                                        return ""

                                conceptos = get_field(current_line, field_boundaries["Conceptos"][0] - 3, field_boundaries["Conceptos"][1] - 2)
                                referencias = get_field(current_line, field_boundaries["Referencias"][0] - 2, field_boundaries["Referencias"][1])
                                debitos_field = get_field(current_line, field_boundaries["Referencias"][1] + 1, field_boundaries["Débitos"][1] + 1)
                                creditos_field = get_field(current_line, field_boundaries["Créditos"][0], field_boundaries["Créditos"][1])
                                saldo_field = get_field(current_line, field_boundaries["Saldo"][0], field_boundaries["Saldo"][1])

                                # Log extracted fields
                                st.info(f"Extracted fields - Conceptos: '{conceptos}', Referencias: '{referencias}', Débitos: '{debitos_field}', Créditos: '{creditos_field}', Saldo: '{saldo_field}'")

                                # Handle multi-line "Conceptos" and "Referencias" if necessary
                                while (not currency_regex.search(debitos_field) and
                                       not currency_regex.search(creditos_field) and
                                       not currency_regex.search(saldo_field)) and i < len(lines) -1:
                                    i += 1
                                    next_line = lines[i].strip()
                                    conceptos += ' ' + get_field(next_line, field_boundaries["Conceptos"][0], field_boundaries["Conceptos"][1])
                                    referencias += ' ' + get_field(next_line, field_boundaries["Referencias"][0], field_boundaries["Referencias"][1])
                                    debitos_field = get_field(next_line, field_boundaries["Débitos"][0], field_boundaries["Débitos"][1])
                                    creditos_field = get_field(next_line, field_boundaries["Créditos"][0], field_boundaries["Créditos"][1])
                                    saldo_field = get_field(next_line, field_boundaries["Saldo"][0], field_boundaries["Saldo"][1])

                                    # Log updated fields after multi-line
                                    st.info(f"After multi-line - Conceptos: '{conceptos}', Referencias: '{referencias}', Débitos: '{debitos_field}', Créditos: '{creditos_field}', Saldo: '{saldo_field}'")

                                transaction["Conceptos"] = conceptos
                                transaction["Referencias"] = referencias

                                # Handle "Saldo Anterior" special case
                                if "saldo anterior" in conceptos.lower() or "saldo anterior" in referencias.lower():
                                    transaction["Conceptos"] = "Saldo Anterior"
                                    transaction["Referencias"] = ""
                                    transaction["Débitos"] = ""
                                    # Assign 'Saldo' from 'Créditos' field
                                    saldo_match = currency_regex.search(creditos_field)
                                    if saldo_match:
                                        transaction["Saldo"] = saldo_match.group()
                                    else:
                                        transaction["Saldo"] = ""
                                    transaction["Créditos"] = ""

                                    if transaction["Saldo"]:
                                        saldo_carry = to_float(transaction["Saldo"])
                                else:
                                    # Determine Débitos and Créditos
                                    debitos_match = currency_regex.search(debitos_field)
                                    creditos_match = currency_regex.search(creditos_field)

                                    if debitos_match:
                                        transaction["Débitos"] = debitos_match.group()
                                    if creditos_match:
                                        transaction["Créditos"] = creditos_match.group()

                                    # Determine Saldo
                                    saldo_match = currency_regex.search(saldo_field)
                                    if saldo_match:
                                        transaction["Saldo"] = saldo_match.group()

                                    # Calculate and verify Saldo
                                    if saldo_carry is not None and transaction["Saldo"]:
                                        deb = to_float(transaction["Débitos"]) if transaction["Débitos"] else 0.0
                                        cred = to_float(transaction["Créditos"]) if transaction["Créditos"] else 0.0
                                        saldo_carry = saldo_carry - deb + cred
                                        # Format saldo_carry back to string with comma as decimal separator
                                        transaction["Saldo"] = f"{saldo_carry:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

                                # Log the transaction being added
                                st.info(f"Transaction to add: {transaction}")

                                transactions.append(transaction)
                                st.success(f"Added transaction: {transaction}")
                                i += 1  # Move to the next line after processing transaction
                            except Exception as e:
                                st.error(f"Error parsing transaction at page {page_index + 1}, line {i + 1}: {e}")
                                i += 1  # Prevent infinite loop by moving to the next line
                                continue
                        else:
                            i += 1  # Move to next line if current line doesn't start with a date
                else:
                    i += 1  # Move to next line if not in DETALLE DE MOVIMIENTOS

        # Handle special cases for first and last transactions
        if transactions:
            # First transaction (Saldo Anterior)
            first_transaction = transactions[0]
            if "Saldo Anterior" in first_transaction["Conceptos"]:
                first_transaction["Conceptos"] = "Saldo Anterior"
                first_transaction["Referencias"] = ""
                first_transaction["Débitos"] = ""
                first_transaction["Créditos"] = ""

            # Last transaction (Saldo al)
            last_transaction = transactions[-1]
            if last_transaction["Conceptos"] == "Saldo":
                last_transaction["Referencias"] = ""
                last_transaction["Débitos"] = ""
                last_transaction["Créditos"] = ""

        st.write(transactions)
        return transactions









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