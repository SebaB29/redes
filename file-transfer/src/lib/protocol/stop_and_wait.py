import logging
import socket
from lib.packet import Packet
from lib.protocol.base import BaseProtocol
from lib.constants import PACKET, STOP_AND_WAIT


class StopAndWait(BaseProtocol):
    """Implementación del protocolo Stop & Wait.

    Envía un paquete a la vez y aguarda su confirmación (ACK) antes de transmitir
    el siguiente. Controla retransmisiones por timeout, descarte de paquetes duplicados
    y filtrado de mensajes pertenecientes a otras transferencias activas.

    Attributes:
        sock (socket.socket): Socket UDP utilizado para la comunicación.
        peer_addr (Tuple[str, int]): Dirección IP y puerto del extremo remoto.
        transfer_id (int): Identificador único de la transferencia actual.
        timeout (float): Tiempo de espera en segundos antes de retransmitir.
        max_retries (int): Cantidad máxima de reintentos por paquete antes de abortar.
        seq (int): Número de secuencia actual del emisor (0 o 1).
        expected_seq (int): Número de secuencia esperado por el receptor (0 o 1).
    """

    def __init__(
        self, sock, peer_addr, transfer_id: int, timeout: float, max_retries: int
    ) -> None:
        """Inicializa una instancia del protocolo Stop & Wait.

        Args:
            sock (socket.socket): Socket UDP preconfigurado.
            peer_addr (Tuple[str, int]): Tupla con la IP y puerto del destino.
            transfer_id (int): ID identificador de la transferencia de archivos.
            timeout (float): Tiempo de espera en segundos antes de retransmitir.
            max_retries (int): Número máximo de intentos de retransmisión.
        """
        super().__init__(sock, peer_addr, transfer_id, timeout)
        self.max_retries = max_retries
        self.seq = 0
        self.expected_seq = 0
        sock.settimeout(STOP_AND_WAIT["timeout"])

    def receive_file(self, dst_path: str) -> None:
        """Recibe un archivo completo mediante Stop & Wait y lo escribe en
        disco.

        Mantiene el bucle de recepción escuchando fragmentos del archivo. Escribe los
        bloques válidos en orden, envía los ACKs correspondientes y gestiona los
        reintentos por timeout hasta recibir el paquete de finalización (END).

        Args:
            dst_path (str): Ruta local de destino para guardar el archivo.
        """
        logging.info(f"[RECEPTOR] Transferencia {self.transfer_id} iniciada")
        with open(dst_path, "wb") as file:
            retries = 0
            while retries < self.max_retries:
                try:
                    data, addr = self.sock.recvfrom(2048)
                    packet = Packet.decode(data)
                except socket.timeout:
                    retries += 1
                    logging.debug(
                        f"[RECEPTOR] Timeout esperando datos ({retries}/{self.max_retries})..."
                    )
                    continue
                except ValueError as e:
                    logging.error(f"[RECEPTOR] Error al decodificar paquete: {e}")
                    continue

                # Filtrar paquetes que no correspondan a esta transferencia
                if packet.transfer_id != self.transfer_id:
                    continue

                # Resetear el contador de timeouts al recibir un paquete válido
                retries = 0

                if (
                    packet.type == PACKET["TYPES"]["DATA"]
                    and packet.seq == self.expected_seq
                ):
                    logging.debug(
                        f"[RECEPTOR] S&W DATA recibido: SEQ={packet.seq}, SIZE={len(packet.payload)}"
                    )
                    file.write(packet.payload)
                    self._send_ack(ack_seq=packet.seq, addr=addr)
                    self.expected_seq = 1 - self.expected_seq

                elif packet.type == PACKET["TYPES"]["END"]:
                    self._send_ack(ack_seq=packet.seq, addr=addr)
                    logging.info("[RECEPTOR] Recepción de archivo completada.")
                    return

                else:
                    # Paquete duplicado o fuera de orden: reenviar el ACK del último paquete recibido correctamente
                    last_received_seq = 1 - self.expected_seq
                    self._send_ack(ack_seq=last_received_seq, addr=addr)

        logging.error(
            "[STOP_AND_WAIT] Tiempo de espera agotado sin recibir datos del emisor."
        )

    def send_file(self, src_path: str) -> None:
        """Envía un archivo completo utilizando el protocolo Stop & Wait.

        Lee el archivo especificado bloque a bloque y lo transmite.
        Garantiza la entrega esperando un ACK antes de procesar y
        enviar el siguiente fragmento. Al finalizar, transmite el paquete END.

        Args:
            src_path (str): Ruta local del archivo a transmitir.
        """
        logging.info(f"[EMISOR] Transferencia {self.transfer_id} iniciada")
        with open(src_path, "rb") as file:
            block = file.read(PACKET["MAX_PAYLOAD_SIZE"])
            while block:

                data_Packet = Packet(
                    type=PACKET["TYPES"]["DATA"],
                    transfer_id=self.transfer_id,
                    seq=self.seq,
                    payload=block,
                )
                data_Packet_bytes = data_Packet.encode()

                retries = 0
                while retries < self.max_retries:
                    self.sock.sendto(data_Packet_bytes, self.peer_addr)
                    logging.debug(f"[EMISOR] Paquete enviado SEQ={self.seq}")
                    if self._wait_for_ack():
                        break

                    retries += 1

                if retries >= self.max_retries:
                    logging.error(
                        "[EMISOR] Límite de reintentos alcanzado en envío de datos."
                    )
                    return

                # Leer el siguiente bloque de datos del archivo
                block = file.read(PACKET["MAX_PAYLOAD_SIZE"])

        self._send_end_Packet()

    def _wait_for_ack(self) -> bool:
        """Espera la llegada del paquete ACK correspondiente al paquete actual.

        Bloquea el socket hasta recibir un paquete de datos o expirar el timeout.
        Verifica que el paquete sea un ACK válido, que corresponda al `transfer_id`
        y que contenga el número de secuencia esperado.

        Returns:
            bool: True si se recibió el ACK esperado correctamente, False en caso de timeout
            o paquete no coincidente.
        """
        try:
            data, _ = self.sock.recvfrom(2048)
            ack = Packet.decode(data)

            if (
                ack.transfer_id == self.transfer_id
                and ack.type == PACKET["TYPES"]["ACK"]
                and ack.ack == self.seq
            ):
                logging.debug(f"[EMISOR] ACK SEQ={self.seq}")
                self.seq = 1 - self.seq
                return True

        except socket.timeout:
            logging.debug(f"[EMISOR] Timeout esperando ACK SEQ={self.seq}")

        return False

    def _send_ack(self, ack_seq: int, addr: tuple) -> None:
        """Construye y envía un paquete ACK de confirmación al receptor.

        Args:
            ack_seq (int): Número de secuencia del paquete que se está confirmando (0 o 1).
            addr (Tuple[str, int]): Dirección de red (IP, puerto) a la cual enviar el ACK.
        """
        ack = Packet(
            type=PACKET["TYPES"]["ACK"],
            transfer_id=self.transfer_id,
            ack=ack_seq,
            seq=ack_seq,
        )
        self.sock.sendto(ack.encode(), addr)
        logging.debug(f"[RECEPTOR] S&W ACK SEQ={ack_seq} enviado")

    def _send_end_Packet(self) -> None:
        """Envía el paquete de finalización (END) de la transferencia.

        Reintenta la transmisión del paquete END hasta recibir su confirmación
        ACK o hasta alcanzar el número máximo de reintentos configurados en
        `max_retries`.
        """
        end_Packet = Packet(
            type=PACKET["TYPES"]["END"],
            transfer_id=self.transfer_id,
            seq=self.seq,
        )
        end_Packet_bytes = end_Packet.encode()

        retries = 0
        while retries < self.max_retries:
            self.sock.sendto(end_Packet_bytes, self.peer_addr)
            logging.debug("[RECEPTOR] S&W END enviado")

            if self._wait_for_ack():
                logging.info(
                    f"[EMISOR] Transferencia finalizada exitosamente. SEQ={end_Packet.seq}"
                )
                return

            retries += 1

        logging.error("[EMISOR] No se recibió ACK del paquete END.")
