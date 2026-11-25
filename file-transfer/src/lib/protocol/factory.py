from lib.constants import SELECTIVE_REPEAT, STOP_AND_WAIT
from lib.protocol.selective_repeat import SelectiveRepeat
from lib.protocol.stop_and_wait import StopAndWait


def build_protocol(
    sock, peer_addr: tuple, transfer_id: int, protocol_code: int, timeout: float = 0
):
    """Instancia la implementación del protocolo según el código especificado.

    Args:
        sock (socket.socket): Socket UDP inicializado para la comunicación.
        peer_addr (Tuple[str, int]): Dirección IP y puerto del extremo remoto.
        transfer_id (int): Identificador único asignado a la transferencia.
        protocol_code (int): Código numérico que identifica el protocolo deseado.
        timeout (float): Tiempo de espera en segundos para las operaciones del protocolo. Si no se especifica o es 0, toma las
            configuraciones por defecto de `constants.py`. Defaults to 0.

    Returns:
        BaseProtocol: Instancia concreta del protocolo que hereda de `BaseProtocol` (`StopAndWait` o `SelectiveRepeat`).

    Raises:
        ValueError: Si `protocol_code` no se corresponde con ningún protocolo soportado.
    """
    if protocol_code == STOP_AND_WAIT["id"]:
        return StopAndWait(
            sock,
            peer_addr,
            transfer_id,
            STOP_AND_WAIT["timeout"],
            STOP_AND_WAIT["max_retries"],
        )
    if protocol_code == SELECTIVE_REPEAT["id"]:
        return SelectiveRepeat(
            sock, peer_addr, transfer_id, SELECTIVE_REPEAT["timeout"]
        )

    raise ValueError(f"Código de protocolo no soportado: {protocol_code}")
