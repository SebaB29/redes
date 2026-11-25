import os
import socket
import tempfile
import unittest

from lib.packet import Packet
from lib.protocol.factory import build_protocol
from lib.protocol.selective_repeat import BucleReceptor, SelectiveRepeat
from lib.protocol.stop_and_wait import StopAndWait
from lib.constants import STOP_AND_WAIT, SELECTIVE_REPEAT, PACKET


class DummySocket:
    def __init__(self, packets):
        self.packets = list(packets)
        self.sent = []
        self.timeout = None

    def settimeout(self, timeout):
        self.timeout = timeout

    def recvfrom(self, size):
        if not self.packets:
            raise socket.timeout()
        return self.packets.pop(0), ("127.0.0.1", 4000)

    def sendto(self, data, addr):
        self.sent.append((data, addr))


class ProtocolFactoryTests(unittest.TestCase):
    def test_build_protocol_returns_expected_implementation(self):
        sw = build_protocol(
            sock=None,
            peer_addr=("127.0.0.1", 7777),
            transfer_id=1,
            protocol_code=STOP_AND_WAIT["id"],
        )
        sr = build_protocol(
            sock=None,
            peer_addr=("127.0.0.1", 7777),
            transfer_id=2,
            protocol_code=SELECTIVE_REPEAT["id"],
        )

        self.assertIsInstance(sw, StopAndWait)
        self.assertIsInstance(sr, SelectiveRepeat)

    def test_unknown_protocol_raises_value_error(self):
        with self.assertRaises(ValueError):
            build_protocol(
                sock=None,
                peer_addr=("127.0.0.1", 7777),
                transfer_id=3,
                protocol_code=999,
            )


class PacketShadowingRegressionTests(unittest.TestCase):
    def test_stop_and_wait_receive_file_does_not_shadow_packet_class(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            dst = os.path.join(tmpdir, "out.bin")
            data_packet = Packet(
                type=PACKET["TYPE"]["DATA"], transfer_id=1, seq=0, payload=b"abc"
            ).encode()
            end_packet = Packet(
                type=PACKET["TYPE"]["END"], transfer_id=1, seq=0
            ).encode()
            sock = DummySocket([data_packet, end_packet])

            protocol = StopAndWait(
                sock,
                ("127.0.0.1", 9000),
                1,
                STOP_AND_WAIT["timeout"],
                STOP_AND_WAIT["max_retries"],
            )
            protocol.receive_file(dst)

            with open(dst, "rb") as f:
                self.assertEqual(f.read(), b"abc")

    def test_selective_repeat_receptor_does_not_shadow_packet_class(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            dst = os.path.join(tmpdir, "out.bin")
            data_packet = Packet(
                type=PACKET["TYPE"]["DATA"], transfer_id=1, seq=1, payload=b"xyz"
            ).encode()
            end_packet = Packet(
                type=PACKET["TYPE"]["END"], transfer_id=1, seq=1
            ).encode()
            sock = DummySocket([data_packet, end_packet])

            BucleReceptor.receive_file(
                sock=sock,
                peer_addr=("127.0.0.1", 9001),
                transfer_id=1,
                dst_path=dst,
            )

            with open(dst, "rb") as f:
                self.assertEqual(f.read(), b"xyz")
