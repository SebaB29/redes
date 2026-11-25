STOP_AND_WAIT = {
    "id": 1,
    "timeout": 0.05,
    "max_retries": 50,
}

SELECTIVE_REPEAT = {
    "id": 2,
    "timeout": 0.08,
    "window_size": 60,
}

PACKET = {
    "TYPES": {
        "START": 1,
        "ACK": 2,
        "DATA": 3,
        "END": 4,
        "ERROR": 5,
    },
    "HEADER_SIZE": 16,
    "MAX_PAYLOAD_SIZE": 1400,
    "FLAGS": {
        "NO_FLAGS": 0,
        "EOF": 1,
    },
}

OPERATION_TYPES = {
    "UPLOAD": 1,
    "DOWNLOAD": 2,
}

DEFAULT_PORT = 7777
