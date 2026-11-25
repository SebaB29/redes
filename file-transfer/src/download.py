import logging
import os
import threading
from lib.handshake import client_handshake
from lib.modo_debug import setup_logger
from lib.parser import parse_download_args
from lib.protocol.factory import build_protocol
from lib.constants import OPERATION_TYPES


def main():
    args = parse_download_args()
    setup_logger(args.verbose, args.quiet)

    # Validar que el directorio de destino exista
    dst_dir = os.path.dirname(args.dst)
    if dst_dir and not os.path.exists(dst_dir):
        logging.error(f"[ERROR] El directorio de destino '{dst_dir}' no existe.")
        return

    sock, server_addr, transfer_id = client_handshake(
        host=args.host,
        port=args.port,
        operation=OPERATION_TYPES["DOWNLOAD"],
        filename=args.name,
        protocol_code=args.protocol_code,
    )

    if not sock:
        logging.error("[ERROR] Falló la conexión inicial con el servidor.")
        return

    threading.main_thread().name = f"transfer-{transfer_id}"
    with sock:
        receiver = build_protocol(
            sock=sock,
            peer_addr=server_addr,
            transfer_id=transfer_id,
            protocol_code=args.protocol_code,
        )
        receiver.receive_file(args.dst)


if __name__ == "__main__":
    main()
