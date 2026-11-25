# 🌐 Redes

Repositorio que reúne dos trabajos prácticos de redes, desarrollados en **Python 3** y probados con **Mininet**: una aplicación de transferencia confiable de archivos sobre UDP y un router con traducción de direcciones y puertos (PAT) sobre redes definidas por software (SDN).

---

## 📦 Proyectos Incluidos

* **`file-transfer/`:** Aplicación cliente-servidor concurrente para subir (`upload.py`) y descargar (`download.py`) archivos sobre UDP mediante protocolos de recuperación de errores a nivel de aplicación (**Stop & Wait** y **Selective Repeat**). Incluye negociación inicial (3-Way Handshake), validación de tramas y pruebas unitarias. Ver [README de File Transfer](file-transfer/README.md).
* **`sdn-nat/`:** Implementación de un router SDN con soporte para **PAT** sobre OpenFlow 1.0 utilizando el controlador **POX** (`protorouter.py` y `flujos.py` dentro de `pox/ext/`) y topologías emuladas en **Mininet** (`topo.py`). Gestiona resolución ARP y traducción dinámica de sesiones TCP y UDP entre una red privada y una red pública. Ver [README de SDN - NAT](sdn-nat/README.md).

---

## 🗂️ Estructura del Repositorio

```text
redes/
├── file-transfer/
│   ├── src/
│   │   ├── lib/
│   │   │   ├── protocol/
│   │   │   │   ├── base.py
│   │   │   │   ├── factory.py
│   │   │   │   ├── selective_repeat.py
│   │   │   │   └── stop_and_wait.py
│   │   │   ├── constants.py
│   │   │   ├── handshake.py
│   │   │   ├── modo_debug.py
│   │   │   ├── packet.py
│   │   │   ├── parser.py
│   │   │   └── server_handler.py
│   │   ├── tests/
│   │   │   └── test_protocol_factory.py
│   │   ├── download.py
│   │   ├── start_server.py
│   │   └── upload.py
│   └── README.md
├── sdn-nat/
│   ├── pox/
│   │   ├── ext/
│   │   │   ├── flujos.py
│   │   │   ├── nat.py
│   │   │   ├── protorouter.py
│   │   │   └── skeleton.py
│   │   ├── pox/
│   │   └── pox.py
│   ├── README.md
│   └── topo.py
└── README.md
```

---

## ⚙️ Requisitos Generales

| Herramienta / Entorno | Propósito |
| :--- | :--- |
| **Linux (Ubuntu / Debian)** | Entorno recomendado para emulación de red y controladores SDN |
| **Python 3** | Ejecución de scripts de cliente/servidor, topologías y componentes |
| **Mininet** | Emulación de topologías, switches virtuales y condiciones de red (delay y pérdida) |
| **POX** | Controlador SDN OpenFlow incluido en `sdn-nat/pox/` |
| **Wireshark / `flake8`** | Análisis de tráfico de red y verificación de estilo PEP 8 en `file-transfer` |

---
