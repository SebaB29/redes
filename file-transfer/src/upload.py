import logging
import os
import threading
from lib.handshake import client_handshake
from lib.modo_debug import setup_logger
from lib.parser import parse_upload_args
from lib.protocol.factory import build_protocol
from lib.constants import OPERATION_TYPES


def main():
    args = parse_upload_args()
    setup_logger(args.verbose, args.quiet)

    # Validar existencia del archivo local antes de iniciar comunicación
    if not os.path.exists(args.src):
        logging.error(f"[ERROR] El archivo de origen '{args.src}' no existe.")
        return

    sock, server_addr, transfer_id = client_handshake(
        host=args.host,
        port=args.port,
        operation=OPERATION_TYPES["UPLOAD"],
        filename=args.name,
        protocol_code=args.protocol_code,
    )

    if not sock:
        logging.error("[ERROR] Falló la conexión inicial con el servidor.")
        return

    threading.main_thread().name = f"transfer-{transfer_id}"
    with sock:
        sender = build_protocol(
            sock=sock,
            peer_addr=server_addr,
            transfer_id=transfer_id,
            protocol_code=args.protocol_code,
        )
        sender.send_file(args.src)


if __name__ == "__main__":
    main()
