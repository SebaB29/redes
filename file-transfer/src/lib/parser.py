import argparse
from lib.constants import STOP_AND_WAIT, SELECTIVE_REPEAT, DEFAULT_PORT


def _add_common_arguments(parser: argparse.ArgumentParser) -> None:
    """Agrega los argumentos comunes de configuración (verbosidad, host y
    puerto) a una instancia existente de ArgumentParser.

    Args:
        parser (argparse.ArgumentParser): Objeto parser al que se le añadirán las opciones comunes.
    """
    verbosity_group = parser.add_mutually_exclusive_group()
    verbosity_group.add_argument(
        "-v", "--verbose", action="store_true", help="Aumenta la verbosidad"
    )
    verbosity_group.add_argument(
        "-q", "--quiet", action="store_true", help="Disminuye la verbosidad"
    )

    parser.add_argument(
        "-H",
        "--host",
        type=str,
        default="127.0.0.1",
        help="Dirección IP del servidor",
    )
    parser.add_argument(
        "-p", "--port", type=int, default=DEFAULT_PORT, help="Puerto del servidor"
    )


def parse_upload_args() -> argparse.Namespace:
    """Parsea los argumentos de la línea de comandos para el cliente de subida
    (upload.py).

    Configura y procesa las opciones para especificar el archivo de origen, el
    nombre de destino en el servidor y el protocolo de transferencia RDT a
    utilizar.
    """
    parser = argparse.ArgumentParser(
        description="Cliente para subir archivos al servidor mediante RDT/UDP"
    )
    _add_common_arguments(parser)

    parser.add_argument(
        "-s",
        "--src",
        type=str,
        required=True,
        help="Ruta del archivo de origen a subir",
    )
    parser.add_argument(
        "-n",
        "--name",
        type=str,
        required=True,
        help="Nombre con el que se guardará el archivo en el servidor",
    )
    parser.add_argument(
        "-r",
        "--protocol",
        type=str,
        choices=["stop-and-wait", "selective-repeat"],
        default="stop-and-wait",
        help="Protocolo de recuperación de errores",
    )

    args = parser.parse_args()
    args.protocol_code = (
        STOP_AND_WAIT["id"]
        if args.protocol == "stop-and-wait"
        else SELECTIVE_REPEAT["id"]
    )
    return args


def parse_download_args() -> argparse.Namespace:
    """Parsea los argumentos de la línea de comandos para el cliente de
    descarga (download.py).

    Configura y procesa las opciones para especificar la ruta local de destino,
    el nombre del archivo a descargar y el protocolo RDT seleccionado.
    """
    parser = argparse.ArgumentParser(
        description="Cliente para descargar archivos del servidor mediante RDT/UDP"
    )
    _add_common_arguments(parser)

    parser.add_argument(
        "-d",
        "--dst",
        type=str,
        required=True,
        help="Ruta donde se guardará el archivo descargado",
    )
    parser.add_argument(
        "-n",
        "--name",
        type=str,
        required=True,
        help="Nombre del archivo a descargar del servidor",
    )
    parser.add_argument(
        "-r",
        "--protocol",
        type=str,
        choices=["stop-and-wait", "selective-repeat"],
        default="stop-and-wait",
        help="Protocolo de recuperación de errores",
    )

    args = parser.parse_args()
    args.protocol_code = (
        STOP_AND_WAIT["id"]
        if args.protocol == "stop-and-wait"
        else SELECTIVE_REPEAT["id"]
    )
    return args


def parse_server_args() -> argparse.Namespace:
    """Parsea los argumentos de la línea de comandos para el servidor
    (start_server.py).

    Configura la dirección IP de escucha, el puerto y el directorio de
    almacenamiento donde se guardarán o leerán los archivos.
    """
    parser = argparse.ArgumentParser(
        description="Servidor de transferencia de archivos RDT/UDP"
    )

    verbosity_group = parser.add_mutually_exclusive_group()
    verbosity_group.add_argument(
        "-v", "--verbose", action="store_true", help="Aumenta la verbosidad"
    )
    verbosity_group.add_argument(
        "-q", "--quiet", action="store_true", help="Disminuye la verbosidad"
    )

    parser.add_argument(
        "-H",
        "--host",
        type=str,
        default="0.0.0.0",
        help="Dirección IP del servicio",
    )
    parser.add_argument(
        "-p", "--port", type=int, default=DEFAULT_PORT, help="Puerto del servicio"
    )
    parser.add_argument(
        "-s",
        "--storage",
        type=str,
        default="./storage",
        help="Ruta del directorio de almacenamiento de archivos",
    )

    return parser.parse_args()
