import logging
import socket
from lib.packet import Packet
from lib.constants import PACKET


def client_handshake(
    host: str, port: int, operation: int, filename: str, protocol_code: int
):
    """Inicia y gestiona la negociación de tres vías (3-Way Handshake) desde el
    cliente.

    Secuencia del Handshake:
        1. Cliente -> Servidor: Envía un paquete `START`.
        2. Servidor Worker -> Cliente: Responde con `ACK` de `START`, enviando el `transfer_id` asignado.
        3. Cliente -> Servidor Worker: Envía un `ACK` final de confirmación para concluir el establecimiento del enlace.

    Args:
        host (str): Dirección IP o nombre de host del servidor.
        port (int): Puerto UDP principal de escucha del servidor.
        operation (int): Código de la operación deseada (e.g., UPLOAD o DOWNLOAD).
        filename (str): Nombre del archivo involucrado en la transferencia.
        protocol_code (int): Código del protocolo de transferencia (STOP_AND_WAIT o SELECTIVE_REPEAT).

    Returns:
        Una tupla con tres elementos:
        - `sock`: Socket UDP configurado para la comunicación, o `None` si falla.
        - `server_addr`: Tupla `(IP, puerto_efimero)` del worker del servidor, o `None` si falla.
        - `transfer_id`: Identificador único de transferencia otorgado por el servidor, o `None` si falla.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # Armar payload: [OPERACION (1B)][PROTOCOLO (1B)][NOMBRE_ARCHIVO]
    payload = bytes([operation]) + bytes([protocol_code]) + filename.encode("utf-8")
    start_packet = Packet(
        type=PACKET["TYPES"]["START"], transfer_id=0, seq=0, payload=payload
    )

    server_addr = (host, port)
    max_intentos = 50
    intentos = 0
    sock.settimeout(0.05)

    # 1. Enviar paquete START al puerto principal
    sock.sendto(start_packet.encode(), server_addr)
    logging.info(f"[CLIENTE] 1/3 START enviado a {server_addr}. SEQ={start_packet.seq}")

    while intentos < max_intentos:
        try:
            # 2. Recibir ACK de START desde el worker del servidor (puerto efímero)
            data, worker_addr = sock.recvfrom(2048)
            ack_packet = Packet.decode(data)

            # Validar que sea un ACK válido y que contenga un transfer_id asignado
            if (
                ack_packet.type != PACKET["TYPES"]["ACK"]
                or ack_packet.transfer_id == 0
                or ack_packet.ack != 0
            ):
                logging.warning(
                    "[CLIENTE] Paquete recibido no es un ACK de START válido. Ignorando."
                )
                continue

            # Actualizar la dirección del servidor a la IP:Puerto efímero del worker
            server_addr = worker_addr
            logging.info(
                f"[CLIENTE] 2/3 ACK de START recibido de {server_addr}. "
                f"Transfer ID: {ack_packet.transfer_id}"
            )

            # 3. Enviar confirmación final al socket dedicado del servidor (Tercer paso del 3-Way Handshake)
            final_ack = Packet(
                type=PACKET["TYPES"]["ACK"],
                transfer_id=ack_packet.transfer_id,
                seq=0,
                ack=0,
            )
            sock.sendto(final_ack.encode(), server_addr)
            logging.info("[CLIENTE] 3/3 Handshake (3-Way) completado exitosamente.")

            return sock, server_addr, ack_packet.transfer_id

        except socket.timeout:
            intentos += 1
            logging.warning(
                f"[CLIENTE] Timeout al esperar ACK de START. "
                f"Reintentando ({intentos}/{max_intentos})..."
            )
            sock.sendto(start_packet.encode(), (host, port))

    logging.error(
        "[CLIENTE] No se pudo completar el handshake después de agotar los reintentos."
    )
    sock.close()
    return None, None, None
