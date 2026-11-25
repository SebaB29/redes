import logging
import os
import random
import socket
import threading
from lib.packet import Packet, decode_start_payload
from lib.protocol.factory import build_protocol
from lib.constants import PACKET, OPERATION_TYPES


class ServerHandler:
    """Manejador de conexiones concurrentes y dispatch de transferencias para
    el servidor.

    Recibe los datagramas entrantes desde el socket UDP principal del servidor.
    Ante la llegada de una solicitud de inicio (`START`), delega la sesión a un puerto
    efímero exclusivo ejecutando un hilo worker dedicado (`threading.Thread`),
    permitiendo atender múltiples clientes en paralelo sin bloquear el puerto principal.

    Attributes:
        storage_dir (str): Ruta del directorio local donde el servidor almacena
            los archivos subidos o desde donde lee los archivos solicitados para descarga.
    """

    def __init__(self, storage_dir: str) -> None:
        """Inicializa el manejador del servidor con el directorio de
        almacenamiento.

        Args:
            storage_dir (str): Directorio raíz de almacenamiento de archivos del servidor.
        """
        self.storage_dir = storage_dir

    def dispatch(self, data: bytes, addr: tuple) -> None:
        """Procesa y filtra datagramas entrantes en el socket principal del
        servidor.

        Decodifica el paquete UDP y, si corresponde a una solicitud `START`, inicia el
        proceso de negociación de Handshake delegando en `_handle_start`.

        Args:
            data (bytes): Buffer binario del datagrama UDP recibido.
            addr (Tuple[str, int]): Dirección `(IP, puerto)` origen del cliente sender.
        """
        try:
            packet = Packet.decode(data)
        except Exception as e:
            logging.error(f"[SERVIDOR] Error al decodificar paquete: {e}")
            return

        if packet.type == PACKET["TYPES"]["START"]:
            self._handle_start(packet, addr)
        else:
            logging.debug(
                f"[SERVIDOR] Paquete tipo {packet.type} ignorado en socket principal."
            )

    def _handle_start(self, packet: Packet, addr: tuple) -> None:
        """Decodifica el payload de la solicitud START e instancia un worker en
        un puerto efímero.

        Extrae la operación solicitada (`UPLOAD`/`DOWNLOAD`), el código de protocolo y el nombre del archivo.
        Asigna un `transfer_id` aleatorio único de 32 bits, abre un nuevo socket UDP asignado dinámicamente
        a un puerto efímero (`bind(("0.0.0.0", 0))`) e inicia un hilo en segundo plano (`daemon=True`)
        para gestionar el resto del intercambio con el cliente.

        Args:
            packet (Packet): Objeto del paquete `START` recibido.
            addr (Tuple[str, int]): Dirección `(IP, puerto)` del cliente.
        """
        try:
            operation, protocol_code, filename = decode_start_payload(packet.payload)
        except Exception as e:
            logging.error(f"[SERVIDOR] Error al decodificar payload de START: {e}")
            return

        file_path = os.path.join(self.storage_dir, filename)
        transfer_id = random.randint(1, 2**32 - 1)

        # Socket en puerto efímero exclusivo para la sesión
        worker_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        worker_sock.bind(("0.0.0.0", 0))

        transfer_thread = threading.Thread(
            target=self._run_transfer,
            args=(
                worker_sock,
                addr,
                transfer_id,
                protocol_code,
                operation,
                file_path,
                packet.seq,
            ),
            daemon=True,
            name=f"transfer-{transfer_id}",
        )
        transfer_thread.start()

    def _run_transfer(
        self,
        sock: socket.socket,
        client_addr: tuple,
        transfer_id: int,
        protocol_code: int,
        operation: int,
        file_path: str,
        start_seq: int,
    ) -> None:
        """Ejecuta el ciclo de vida completo de la transferencia dentro de un
        hilo dedicado.

        Args:
            sock (socket.socket): Socket UDP ligado al puerto efímero para esta sesión.
            client_addr (Tuple[str, int]): Dirección `(IP, puerto)` del cliente.
            transfer_id (int): Identificador único de la transferencia.
            protocol_code (int): Código del protocolo negociado (`STOP_AND_WAIT` o `SELECTIVE_REPEAT`).
            operation (int): Tipo de operación (`UPLOAD` o `DOWNLOAD`).
            file_path (str): Ruta completa del archivo destino o fuente en el servidor.
            start_seq (int): Número de secuencia del paquete `START` recibido.
        """
        with sock:
            # Enviar ACK del START desde el socket dedicado (puerto efímero)
            ack_Packet = Packet(
                type=PACKET["TYPES"]["ACK"],
                transfer_id=transfer_id,
                ack=start_seq,
                seq=start_seq,
            )
            sock.sendto(ack_Packet.encode(), client_addr)
            logging.info(
                f"[SERVIDOR] ACK de START enviado para transferencia {transfer_id} desde {sock.getsockname()}"
            )

            try:
                protocol = build_protocol(
                    sock=sock,
                    peer_addr=client_addr,
                    transfer_id=transfer_id,
                    protocol_code=protocol_code,
                )

                if operation == OPERATION_TYPES["UPLOAD"]:
                    logging.info(f"[SERVIDOR] Iniciando UPLOAD: {file_path}")
                    protocol.receive_file(file_path)
                elif operation == OPERATION_TYPES["DOWNLOAD"]:
                    if not os.path.exists(file_path):
                        logging.error(f"[SERVIDOR] Archivo no encontrado: {file_path}")

                        error_Packet = Packet(
                            type=PACKET["TYPES"]["ERROR"],
                            transfer_id=transfer_id,
                            payload="El archivo solicitado no existe en el servidor.".encode(
                                "utf-8"
                            ),
                        )
                        sock.sendto(error_Packet.encode(), client_addr)
                        return

                    logging.info(f"[SERVIDOR] Iniciando DOWNLOAD: {file_path}")
                    protocol.send_file(file_path)
            except Exception as e:
                logging.error(
                    f"[SERVIDOR] Error en la transferencia {transfer_id}: {e}"
                )
