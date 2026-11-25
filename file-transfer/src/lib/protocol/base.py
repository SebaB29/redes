from abc import ABC, abstractmethod


class BaseProtocol(ABC):
    """Clase base abstracta que define la interfaz común para las
    implementaciones de protocolos.

    Attributes:
        sock (socket.socket): Socket UDP utilizado para la comunicación.
        peer_addr (Tuple[str, int]): Dirección IP y puerto del extremo remoto.
        transfer_id (int): Identificador único de la transferencia de archivos.
        timeout (float): Tiempo de espera en segundos para operaciones del socket.
    """

    def __init__(
        self, sock, peer_addr: tuple, transfer_id: int, timeout: float
    ) -> None:
        """Inicializa los parámetros base requeridos por cualquier protocolo.

        Args:
            sock (socket.socket): Socket UDP inicializado para la transmisión/recepción.
            peer_addr (Tuple[str, int]): Tupla (IP, puerto) del host remoto.
            transfer_id (int): Identificador numérico de la sesión de transferencia.
            timeout (float): Tiempo de expiración configurado para el socket.
        """
        self.sock = sock
        self.peer_addr = peer_addr
        self.transfer_id = transfer_id
        self.timeout = timeout

    @abstractmethod
    def send_file(self, src_path: str):
        """Envía un archivo local al extremo remoto de forma confiable.

        Args:
            src_path (str): Ruta del archivo de origen que se desea transmitir.
        """
        pass

    @abstractmethod
    def receive_file(self, dst_path: str):
        """Recibe un archivo transmitido por el extremo remoto y lo almacena
        localmente.

        Args:
            dst_path (str): Ruta local donde se guardará el archivo recibido.
        """
        pass
