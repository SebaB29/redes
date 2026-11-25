from lib.constants import PACKET


def decode_start_payload(payload: bytes) -> tuple[int, int, str]:
    """Decodifica el payload de un paquete de tipo START.

    Extrae la operación solicitada, el protocolo acordado y el nombre del
    archivo objetivo codificado en UTF-8.

    Args:
        payload (bytes) recibido dentro del paquete START.

    Returns:
        tuple[int, int, str]: Una tupla con tres elementos:
            - operation (int): Identificador de la operación.
            - protocol (int): Identificador del protocolo.
            - filename (str): Nombre del archivo a transferir.

    Raises:
        ValueError: Si el payload contiene menos de 2 bytes (insuficiente para extraer la operación y el protocolo).
    """
    if len(payload) < 2:
        raise ValueError("Payload de START demasiado pequeño")

    operation = payload[0]
    protocol = payload[1]
    filename = payload[2:].decode("utf-8")

    return operation, protocol, filename


class Packet:
    """Representa una trama binaria del protocolo de transferencia sobre UDP.

    Contiene un encabezado fijo de 16 bytes serializado en Big-Endian y un payload de tamaño variable.
    Formato del header:
        TYPE (1) + FLAGS (1) + TRANSFER_ID (4) + SEQ (4) + ACK (4) + LENGTH (2)

    Attributes:
        type (int): Tipo de paquete.
        flags (int): Banderas de control de estado (ej. EOF, NO_FLAGS).
        transfer_id (int): Identificador único de la sesión de transferencia.
        seq (int): Número de secuencia del paquete actual.
        ack (int): Número de confirmación de recepción (ACK).
        payload (bytes): Datos adjuntos al paquete.
    """

    def __init__(
        self,
        type: int,
        flags: int = PACKET["FLAGS"]["NO_FLAGS"],
        transfer_id: int = 0,
        seq: int = 0,
        ack: int = 0,
        payload: bytes = b"",
    ) -> None:
        """Inicializa una instancia del paquete.

        Args:
            type (int): Tipo de paquete (1 byte).
            flags (int, optional): Banderas asociadas (1 byte). Por defecto NO_FLAGS.
            transfer_id (int, optional): ID de la transferencia (4 bytes). Por defecto 0.
            seq (int, optional): Número de secuencia (4 bytes). Por defecto 0.
            ack (int, optional): Número de ACK (4 bytes). Por defecto 0.
            payload (bytes, optional): Datos adjuntos al paquete. Por defecto b"".

        Raises:
            ValueError: Si el tamaño de `payload` supera el límite permitido `MAX_PAYLOAD_SIZE`.
        """
        if len(payload) > PACKET["MAX_PAYLOAD_SIZE"]:
            raise ValueError("Payload demasiado grande")

        self.type = type
        self.flags = flags
        self.transfer_id = transfer_id
        self.seq = seq
        self.ack = ack
        self.payload = payload

    def encode(self) -> bytes:
        """Serializa el objeto `Packet` en un arreglo binario.

        Construye el encabezado fijo de 16 bytes codificado en Big-Endian y
        le concatena el payload.

        Returns:
            bytes: Secuencia binaria final que representa todo el paquete.
        """
        header = (
            self.type.to_bytes(1, byteorder="big")
            + self.flags.to_bytes(1, byteorder="big")
            + self.transfer_id.to_bytes(4, byteorder="big")
            + self.seq.to_bytes(4, byteorder="big")
            + self.ack.to_bytes(4, byteorder="big")
            + len(self.payload).to_bytes(2, byteorder="big")
        )

        return header + self.payload

    @classmethod
    def decode(cls, data: bytes):
        """Deserializa un binario y construye un objeto
        `Packet`.

        Extrae los 16 bytes de cabecera en formato Big-Endian y los mapea a los
        atributos correspondientes.

        Args:
            data (bytes): Secuencia binaria recibida por el socket UDP.

        Returns:
            Packet: Una nueva instancia de la clase `Packet` con los campos deserializados.

        Raises:
            ValueError: Si `data` no alcanza el tamaño mínimo de la cabecera
                (`HEADER_SIZE`), o si la longitud declarada en el encabezado
                no coincide con la longitud real del payload recibido.
        """
        if len(data) < PACKET["HEADER_SIZE"]:
            raise ValueError("Paquete demasiado pequeño")

        header = data[: PACKET["HEADER_SIZE"]]
        payload = data[PACKET["HEADER_SIZE"] :]

        # aca "desempaqetamos" byte por byte (de los 16 q tiene el header), usando cortes con los indices
        type_val = int.from_bytes(header[0:1], byteorder="big")
        flags = int.from_bytes(header[1:2], byteorder="big")
        transfer_id = int.from_bytes(header[2:6], byteorder="big")
        seq = int.from_bytes(header[6:10], byteorder="big")
        ack = int.from_bytes(header[10:14], byteorder="big")
        length = int.from_bytes(header[14:16], byteorder="big")

        if len(payload) != length:
            raise ValueError("Longitud del payload incorrecta")

        return cls(
            type=type_val,
            flags=flags,
            transfer_id=transfer_id,
            seq=seq,
            ack=ack,
            payload=payload,
        )
