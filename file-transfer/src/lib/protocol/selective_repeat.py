import logging
import socket
import time

from lib.protocol.base import BaseProtocol
from lib.constants import PACKET, SELECTIVE_REPEAT
from lib.packet import Packet


class SelectiveRepeat(BaseProtocol):
    """Implementación del protocolo Selective Repeat para transferencia de
    datos.

    Attributes:
        sock (socket.socket): Socket UDP utilizado para la comunicación.
        peer_addr (Tuple[str, int]): Dirección IP y puerto del extremo remoto.
        transfer_id (int): Identificador único de la transferencia.
        timeout (float): Tiempo en segundos del socket y retransmisión.
        window_size (int): Tamaño de la ventana.
    """

    def __init__(
        self,
        sock,
        peer_addr: tuple,
        transfer_id: int,
        timeout: float,
        window_size: int = SELECTIVE_REPEAT["window_size"],
    ) -> None:
        """Inicializa el protocolo Selective Repeat.

        Args:
            sock (socket.socket): Socket UDP.
            peer_addr (Tuple[str, int]): IP y puerto del host remoto.
            transfer_id (int): ID de la transferencia de archivos.
            timeout (float): Tiempo límite de expiración para timers y socket.
            window_size (int): Tamaño de la ventana de transmisión/recepción.
                Por defecto utiliza `SELECTIVE_REPEAT["window_size"]`.
        """
        super().__init__(sock, peer_addr, transfer_id, timeout=timeout)
        self.window_size = window_size

    def send_file(self, src_path: str) -> None:
        """Delega el envío del archivo al bucle emisor de Selective Repeat.

        Args:
            src_path (str): Ruta local del archivo de origen a enviar.
        """
        BucleEmisor.send_file(
            sock=self.sock,
            server_addr=self.peer_addr,
            transfer_id=self.transfer_id,
            src_path=src_path,
            window_size=self.window_size,
            timeout=self.timeout,
        )

    def receive_file(self, dst_path: str) -> None:
        """Delega la recepción del archivo al bucle receptor de Selective
        Repeat.

        Args:
            dst_path (str): Ruta destino para guardar el archivo recibido.
        """
        BucleReceptor.receive_file(
            sock=self.sock,
            peer_addr=self.peer_addr,
            transfer_id=self.transfer_id,
            dst_path=dst_path,
            window_size=self.window_size,
            timeout=self.timeout,
        )


class SenderWindow:
    """Gestiona el estado de la ventana del emisor en Selective Repeat.

    Attributes:
        tamanio_ventana (int): Máx de paquetes no confirmados simultáneos.
        send_base (int): Número de secuencia del paquete no confirmado
        más antiguo en la ventana.
        proximo_seq (int): Número de secuencia que se asignará al próximo
        paquete nuevo a transmitir.
        buffer (dict): Diccionario de paquetes que aun no fueron confirmados
        con ACK.
    """

    def __init__(self, tamanio_ventana: int = SELECTIVE_REPEAT["window_size"]) -> None:
        """Inicializa la estructura de datos de la ventana del emisor.

        Args:
            tamanio_ventana (int): Tamaño máximo de la ventana de envío.
                Defaults to `SELECTIVE_REPEAT["window_size"]`.
        """
        self.tamanio_ventana = tamanio_ventana
        self.send_base = 1

        self.proximo_seq = 1
        self.buffer = {}
        """Funciones para manejar los 3 eventos que se dan en el emisor del
        Selective Repeat.

        (1) (Enviar paquete nuevo): Verificar si hay cupo en la ventana.

        (2) (Recibir el ACK): Marcar el paquete correspondiente como
        confirmado.

        (3) (Timeout): Reetransmitir unicamente aquel paquete cuyo timer
        individual haya expirado.
        """

    def puede_enviar(self) -> bool:
        """Verifica si la ventana dispone de cupo para transmitir un paquete
        nuevo.

        Returns:
            bool: True si `proximo_seq` cae dentro del rango de la ventana
            actual, False en caso contrario.
        """
        return self.proximo_seq < (self.send_base + self.tamanio_ventana)

    def registrar_envio(self, paquete) -> None:
        """Registra un paquete recién enviado en la ventana e incrementa el
        contador de secuencia.

        Args:
            paquete (Packet): Objeto del paquete DATA transmitido.
        """
        """Registra que paquete fue enviado y avanza proximo_seq."""
        self.buffer[paquete.seq] = {
            "paquete": paquete,
            "timestamp": time.time(),
            "acked": False,
        }
        self.proximo_seq = paquete.seq + 1

    def recibir_ack(self, ack_num: int) -> bool:
        """Marca el paquete como confirmado y desliza send_base.

        Args:
            ack_num (int): Número de secuencia confirmado por el ACK.

        Returns:
            bool: True si el ACK pertenecía a un paquete pendiente en la
            ventana, False si no existía.
        """
        if ack_num not in self.buffer:
            return False

        # aca marca el paq como confirmado
        self.buffer[ack_num]["acked"] = True

        while self.send_base in self.buffer and self.buffer[self.send_base]["acked"]:
            del self.buffer[self.send_base]
            self.send_base += 1

        return True

    def paquetes_en_timeout(
        self, timeout_segundos: float = SELECTIVE_REPEAT["timeout"]
    ) -> list:
        """Identifica los paquetes cuyo timer de retransmisión ha expirado.

        Itera sobre los paquetes no confirmados en la ventana y compara el
        tiempo transcurrido desde el último envío con el valor de timeout.
        Si expiró, reinicia su marca de tiempo.

        Args:
            timeout_segundos (float): Tiempo límite en segundos para
            considerar expiración.

        Returns:
            List[Packet]: Lista de objetos `Packet` que deben ser
            retransmitidos inmediatamente.
        """
        now = time.time()
        paquetes_para_reenviar = []

        for info in self.buffer.values():
            if not info["acked"] and (now - info["timestamp"]) > timeout_segundos:

                # si no esta acked y (tiempo_actual) - (timestamp de envío)
                # es mas grande que el timeout q establecimos, lo reenviamos
                # y reiniciamos el timer

                paquetes_para_reenviar.append(info["paquete"])
                info["timestamp"] = now

        return paquetes_para_reenviar

    def hay_pendientes(self) -> bool:
        """Informa si aún existen paquetes pendientes de confirmación ACK en la
        ventana.

        Returns:
            bool: True si hay al menos un paquete en el buffer sin deslizar,
            False si está vacío.
        """
        return len(self.buffer) > 0


class ReceiverWindow:
    """Gestiona el buffer de recepción y el ordenamiento de paquetes en
    Selective Repeat.

    Attributes:
        tamanio_ventana (int): Capacidad máxima de paquetes fuera de orden
        almacenables.
        nro_seq_esperado (int): Número de secuencia del paquete que espera
        recibir a continuación.
        buffer (dict): Almacenamiento temporal de paquetes en desorden
        `{seq: Packet}`.
    """

    def __init__(self, tamanio_ventana: int = SELECTIVE_REPEAT["window_size"]) -> None:
        """Inicializa la ventana de recepción.

        Args:
            tamanio_ventana (int): Tamaño máximo de la ventana de recepción.
        """
        self.tamanio_ventana = tamanio_ventana
        self.nro_seq_esperado = 1
        self.buffer = {}

    def esta_dentro_del_rango(self, nro_seq: int) -> bool:
        """Comprueba si un número de secuencia cae dentro de la ventana de
        recepción actual.

        Args:
            nro_seq (int): Número de secuencia a comprobar.

        Returns:
            bool: True si está dentro del límite
            `[nro_seq_esperado, nro_seq_esperado + tamanio_ventana)`.
        """
        limite = self.nro_seq_esperado + self.tamanio_ventana
        return self.nro_seq_esperado <= nro_seq < limite

    def procesar_paquete(self, paquete):
        """Procesa un paquete de datos entrante (DATA) y entrega los bloques
        ordenados.

        Args:
            paquete (Packet): Paquete DATA recibido.

        Returns:
            Tuple[bool, List[Packet]]: Tupla compuesta por:
                - `bool`: True si el paquete es válido/duplicado y requiere
                envío de ACK; False si es totalmente invalido/fuera de rango.
                - `List[Packet]`: Lista ordenada de paquetes listos para
                entregarse a la capa superior.
        """
        if paquete.seq < self.nro_seq_esperado:
            return True, []  # duplicado, ya fue entregado

        if not self.esta_dentro_del_rango(paquete.seq):
            return False, []  # fuera de la ventana, se ignora

        self.buffer[paquete.seq] = paquete
        paquetes_a_entregar = []

        while self.nro_seq_esperado in self.buffer:
            paquetes_a_entregar.append(self.buffer.pop(self.nro_seq_esperado))
            self.nro_seq_esperado += 1

        return True, paquetes_a_entregar


class BucleEmisor:
    """Este bucle emisor vendria a ser el send_file(...) del upload.py pero en
    su version con selective_repeat, osea su version "confiable".

    Toda la logica pesada del bucle vive aca en este file, y no en el upload.py

    Funcion prinicipal: Send_file()

    Funciones auxiliares:
        enviar_data_disponible(),
                recibir_acks(),
                retransmitir_paqs_timeout(),
                enviar_end()
    """

    @staticmethod
    def send_file(
        sock,
        server_addr: tuple,
        transfer_id: int,
        src_path: str,
        window_size: int = SELECTIVE_REPEAT["window_size"],
        timeout: float = 0.10,
    ):
        """Ejecuta el ciclo principal de envío de archivo con Selective Repeat.

        Lee bloques del archivo, los transmite mientras haya espacio en la
        ventana, captura ACKs entrantes, detecta timeouts individuales y
        retransmite. Al finalizar el archivo y vaciarse la ventana, envía la
        señal de finalización (`END`).

        Args:
            sock (socket.socket): Socket UDP para el envío/recepción.
            server_addr (Tuple[str, int]): Dirección IP y puerto del destino.
            transfer_id (int): Identificador de la transferencia.
            src_path (str): Ruta del archivo local a transmitir.
            window_size (int): Tamaño de la ventana de transmisión.
            timeout (float): Tiempo máximo de espera para retransmisiones por
            paquete.
        """
        sock.settimeout(SELECTIVE_REPEAT["timeout"])
        ventana = SenderWindow(tamanio_ventana=window_size)
        archivo_enviado_por_completo = False

        seq = 1
        reintentos_fallidos_seguidos = 0
        MAX_INTENTOS_FALLIDOS = 15

        logging.info(f"[EMISOR] Transferencia {transfer_id} iniciada")
        with open(src_path, "rb") as file:

            while not archivo_enviado_por_completo or ventana.hay_pendientes():

                seq, archivo_enviado_por_completo = BucleEmisor.enviar_data_disponible(
                    sock,
                    server_addr,
                    transfer_id,
                    file,
                    ventana,
                    seq,
                    archivo_enviado_por_completo,
                )

                acks_recibidos_en_esta_vuelta = BucleEmisor.recibir_acks(
                    sock,
                    transfer_id,
                    ventana,
                )

                if acks_recibidos_en_esta_vuelta > 0:
                    reintentos_fallidos_seguidos = 0

                reintentos_fallidos_seguidos = BucleEmisor.retransmitir_paqs_timeout(
                    sock,
                    server_addr,
                    ventana,
                    timeout,
                    reintentos_fallidos_seguidos,
                    MAX_INTENTOS_FALLIDOS,
                )
                if reintentos_fallidos_seguidos is None:
                    return

        BucleEmisor.enviar_end(sock, server_addr, transfer_id, seq, timeout)

    @staticmethod
    def enviar_data_disponible(
        sock,
        server_addr: tuple,
        transfer_id: int,
        file: str,
        ventana,
        seq: int,
        archivo_enviado_por_completo: bool,
    ) -> tuple:
        """Lee bloques de datos del archivo y los envía mientras la ventana
        tenga capacidad disponible.

        Args:
            sock (socket.socket): Socket UDP.
            server_addr (Tuple[str, int]): Dirección de red del destinatario.
            transfer_id (int): Identificador único de transferencia.
            file (file object): Archivo abierto en modo lectura binaria.
            ventana (SenderWindow): Instancia de la ventana del emisor.
            seq (int): Número de secuencia actual para el próximo paquete.
            archivo_enviado_por_completo (bool): Flag de lectura del archivo.

        Returns:
            Tuple[int, bool]: Tupla con el próximo `seq` a usar y la bandera
            actualizada `archivo_enviado_por_completo`.
        """
        while ventana.puede_enviar() and not archivo_enviado_por_completo:
            block = file.read(PACKET["MAX_PAYLOAD_SIZE"])

            if not block:
                archivo_enviado_por_completo = True
                break

            data_Packet = Packet(
                type=PACKET["TYPES"]["DATA"],
                transfer_id=transfer_id,
                seq=seq,
                payload=block,
            )
            sock.sendto(data_Packet.encode(), server_addr)
            ventana.registrar_envio(data_Packet)
            logging.debug(f"[EMISOR] SR DATA enviado: SEQ={seq}, SIZE={len(block)}")
            seq += 1

        return seq, archivo_enviado_por_completo

    @staticmethod
    def recibir_acks(sock, transfer_id: int, ventana) -> int:
        """Lee del socket todos los paquetes ACK recibidos y los procesa en la
        ventana.

        Args:
            sock (socket.socket): Socket configurado con timeout de no bloqueo.
            transfer_id (int): Identificador de transferencia esperado.
            ventana (SenderWindow): Instancia de la ventana del emisor.

        Returns:
            int: Cantidad total de paquetes ACK procesados exitosamente en esta
            llamada.
        """
        acks_recibidos = 0
        while True:
            try:
                data, _ = sock.recvfrom(1400)
                ack_pkg = Packet.decode(data)

                if ack_pkg.type == PACKET["TYPES"]["ACK"] and int(
                    ack_pkg.transfer_id
                ) == int(transfer_id):
                    ventana.recibir_ack(int(ack_pkg.ack))
                    logging.debug(f"[EMISOR] SR ACK SEQ={ack_pkg.seq} recibido")
                    acks_recibidos += 1
            except socket.timeout:
                break

        return acks_recibidos

    @staticmethod
    def retransmitir_paqs_timeout(
        sock,
        server_addr: tuple,
        ventana,
        timeout: float,
        intentos: int,
        max_intentos: int,
    ):
        """Identifica los paquetes vencidos por timeout en la ventana y los
        vuelve a enviar.

        Args:
            sock (socket.socket): Socket UDP.
            server_addr (Tuple[str, int]): Dirección del destino.
            ventana (SenderWindow): Instancia de la ventana del emisor.
            timeout (float): Tiempo de expiración del timer en segundos.
            intentos (int): Contador de reintentos fallidos consecutivos.
            max_intentos (int): Límite máximo permitido de reintentos.

        Returns:
            Optional[int]: El contador de `intentos` actualizado, o `None` si
            se superó el límite de fallos.
        """
        paquetes_timeout = ventana.paquetes_en_timeout(timeout_segundos=timeout)
        if not paquetes_timeout:
            return intentos

        intentos += 1
        if intentos > max_intentos:
            logging.error("[EMISOR] Se paso el limite de intentos fallidos, \
                CLIENTE DESCONECTADO, abortando...")
            return None

        for paquete in paquetes_timeout:
            sock.sendto(paquete.encode(), server_addr)
            logging.debug(f"[EMISOR] SR DATA retransmitido: SEQ={paquete.seq}")

        return intentos

    @staticmethod
    def enviar_end(
        sock, server_addr: tuple, transfer_id: int, seq: int, timeout: float
    ):
        """Construye y retransmite el paquete END de finalización hasta recibir
        su ACK.

        Args:
            sock (socket.socket): Socket UDP.
            server_addr (Tuple[str, int]): Dirección del receptor.
            transfer_id (int): Identificador de la transferencia.
            seq (int): Número de secuencia para el paquete END.
            timeout (float): Tiempo de espera en segundos para aguardar el ACK.
        """
        end_Packet = Packet(
            type=PACKET["TYPES"]["END"], transfer_id=transfer_id, seq=seq
        )
        sock.settimeout(timeout)
        max_intentos_end = 5
        intentos = 0

        while intentos < max_intentos_end:
            sock.sendto(end_Packet.encode(), server_addr)
            logging.info(f"[EMISOR] SR END enviado ({intentos + 1}/{max_intentos_end})")

            try:
                data, _ = sock.recvfrom(1400)
                ack_pkg = Packet.decode(data)
                if (
                    ack_pkg.type == PACKET["TYPES"]["ACK"]
                    and int(ack_pkg.transfer_id) == int(transfer_id)
                    and int(ack_pkg.ack) == int(seq)
                ):
                    logging.info(
                        "[EMISOR] ACK END recibido. Finalizada la transferencia"
                    )
                    break
            except socket.timeout:
                intentos += 1


class BucleReceptor:
    """Este bucle receptor vendria a ser el receive_file(...) del download.py
    pero en su version con selective_repeat, osea su version "confiable".

    Toda la logica pesada del bucle vive aca en este file, y no en el
    downoload.py.

    Funcion principal: receive_file()

    Funciones auxiliares: recibir_paquete(), procesar_data(), enviar_ack_end()
    """

    @staticmethod
    def receive_file(
        sock,
        peer_addr: tuple,
        transfer_id: int,
        dst_path: str,
        window_size: int = SELECTIVE_REPEAT["window_size"],
        timeout: float = SELECTIVE_REPEAT["timeout"],
    ) -> None:
        """Ejecuta el ciclo principal de recepción de archivo con Selective
        Repeat.

        Recibe paquetes por el socket, valida el `transfer_id`, procesa
        paquetes de datos escribiendo los fragmentos en disco en orden correcto
        y emite las respuestas ACK individuales.
        Finaliza al recibir la señal `END`.

        Args:
            sock (socket.socket): Socket UDP.
            peer_addr (Tuple[str, int]): Dirección IP y puerto del emisor.
            transfer_id (int): Identificador de la transferencia esperado.
            dst_path (str): Ruta del archivo local donde se guardan los datos.
            window_size (int): Tamaño de la ventana del receptor.
            timeout (float): Tiempo de expiración del socket en segundos.
        """
        sock.settimeout(timeout)
        ventana = ReceiverWindow(tamanio_ventana=window_size)

        logging.info(f"[RECEPTOR] Transferencia {transfer_id} iniciada")
        with open(dst_path, "wb") as file:
            while True:
                packet = BucleReceptor.recibir_paquete(sock)
                if packet is None:
                    return

                if packet.transfer_id != transfer_id:
                    continue

                if packet.type == PACKET["TYPES"]["DATA"]:
                    BucleReceptor.procesar_data(
                        sock, peer_addr, transfer_id, packet, ventana, file
                    )
                elif packet.type == PACKET["TYPES"]["END"]:
                    BucleReceptor.enviar_ack_end(sock, peer_addr, transfer_id, packet)
                    break

    @staticmethod
    def recibir_paquete(sock):
        """Escucha en el socket y decodifica un paquete UDP entrante.

        Args:
            sock (socket.socket): Socket UDP.

        Returns:
            Optional[Packet]: Objeto `Packet` decodificado, o `None` en caso de
            recibir un paquete de error.
        """
        while True:
            try:
                data, _ = sock.recvfrom(2048)
                packet = Packet.decode(data)
            except socket.timeout:
                continue

            if packet.type == PACKET["TYPES"]["ERROR"]:
                msg_error = packet.payload.decode("utf-8")
                logging.error(f"[EMISOR] Error devuelto del server: {msg_error}")
                return None

            return packet

    @staticmethod
    def procesar_data(
        sock, peer_addr: tuple, transfer_id: int, packet, ventana, file
    ) -> None:
        """Procesa un paquete DATA recibido, escribe los bloques ordenados en
        disco y responde el ACK.

        Args:
            sock (socket.socket): Socket UDP.
            peer_addr (Tuple[str, int]): Dirección del emisor para enviar ACK.
            transfer_id (int): Identificador de la transferencia.
            packet (Packet): Paquete DATA entrante.
            ventana (ReceiverWindow): Instancia de la ventana receptora.
            file (file object): Archivo abierto en modo escritura binaria.
        """
        logging.debug(
            f"[RECEPTOR] SR DATA recibido: SEQ={packet.seq}, "
            f"SIZE={len(packet.payload)}, esperado={ventana.nro_seq_esperado}"
        )
        es_valido_ack, paquetes_listos = ventana.procesar_paquete(packet)

        for paquete in paquetes_listos:
            file.write(paquete.payload)

        if es_valido_ack:
            ack_Packet = Packet(
                type=PACKET["TYPES"]["ACK"],
                transfer_id=transfer_id,
                ack=packet.seq,
                seq=packet.seq,
            )
            sock.sendto(ack_Packet.encode(), peer_addr)
            logging.debug(f"[RECEPTOR] SR ACK SEQ={packet.seq} enviado")

    @staticmethod
    def enviar_ack_end(sock, peer_addr: tuple, t_id: int, packet) -> None:
        """Envía la confirmación ACK final al emisor tras recibir el paquete
        END.

        Args:
            sock (socket.socket): Socket UDP.
            peer_addr (Tuple[str, int]): Dirección del emisor.
            transfer_id (int): Identificador de la transferencia.
            packet (Packet): Paquete de fin de transmisión (END) recibido.
        """
        logging.info("[RECEPTOR] SR END recibido")
        ack_Packet = Packet(
            type=PACKET["TYPES"]["ACK"],
            transfer_id=t_id,
            ack=packet.seq,
            seq=packet.seq,
        )
        sock.sendto(ack_Packet.encode(), peer_addr)
