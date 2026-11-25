import logging
import os
import socket

from lib.modo_debug import setup_logger
from lib.parser import parse_server_args
from lib.server_handler import ServerHandler


def main():
    args = parse_server_args()
    setup_logger(args.verbose, args.quiet)

    os.makedirs(args.storage, exist_ok=True)

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.bind((args.host, args.port))

    if not args.quiet:
        logging.info(f"[SERVIDOR] Escuchando en {args.host}:{args.port}")

    handler = ServerHandler(storage_dir=args.storage)

    while True:
        try:
            data, addr = server_socket.recvfrom(2048)
            handler.dispatch(data, addr)
        except Exception as e:
            logging.error(f"[SERVIDOR] Error al procesar paquete entrante: {e}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logging.info("\n[SERVIDOR] Cerrado con Ctrl + C")
