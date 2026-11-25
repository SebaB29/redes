# 🌐 SDN - NAT (Network Address Translation)

Implementación de un router con soporte para **PAT (Port Address Translation)** sobre redes definidas por software (**SDN**), utilizando el controlador **POX** y el emulador **Mininet**.

---

## 🎯 Descripción del Proyecto

El objetivo principal de este trabajo práctico es desarrollar una aplicación de control SDN capaz de realizar traducción de direcciones y puertos (**PAT**) para habilitar la conectividad saliente de múltiples hosts ubicados dentro de una red privada (`10.0.0.0/24`) hacia una red pública (`200.0.0.0/24`), empleando una única dirección IP pública (`200.0.0.1`).

* **Separación de planos:** El controlador **POX** gestiona la lógica de red y el mapeo de sesiones en el plano de control, instalando reglas dinámicas en el switch OpenFlow (`s1`) para acelerar el reenvío en el plano de datos.
* **Protocolos soportados:** Resolución de tráfico **ARP** y traducción de sesiones **TCP** y **UDP**.

---

## 👥 Integrantes

| Nombre y Apellido |
| :--- |
| Brizuela Sebastian |
| Fraga Fernando |
| Ricardo Tomas Dopacio |
| Colazo Sebastian |
| Guttlein Gareis Alexis |

---

## ⚙️ Requisitos e Instalación

* **Sistema Operativo:** Linux (Ubuntu / Debian recomendado)
* **Python:** Python 3.x (compatible con la versión de POX instalada)
* **Herramientas de red:**
  * [Mininet](http://mininet.org/)
  * Controlador [POX](https://github.com/noxrepo/pox)

---

## 🗂️ Estructura del Repositorio

```text
TP2-SDN-NAT/
├── controlador/
│   ├── flujos.py        # Reglas OpenFlow, timeouts y helpers de construcción de paquetes
│   ├── nat.py           # Módulo auxiliar reservado
│   └── protorouter.py   # Lógica principal de enrutamiento L3, ARP y tabla PAT
├── topologia/
│   └── topo.py          # Definición de topología en Mininet (hosts, switch s1 y enlaces)
└── README.md            # Documentación del proyecto
```

---

## 🕸️ Topología de Red

La topología emulada consiste en un switch central (**`s1`**) que interconecta una subred privada con una red pública:

| Host | Rol | Subred | Dirección IP | Dirección MAC | Puerto en `s1` |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`h1`** | Host Privado 1 | Privada | `10.0.0.10/24` | `00:00:00:00:00:01` | `1` (`s1-eth1`) |
| **`h2`** | Host Privado 2 | Privada | `10.0.0.20/24` | `00:00:00:00:00:02` | `2` (`s1-eth2`) |
| **`h3`** | Host Público / Servidor | Pública | `200.0.0.100/24` | `00:00:00:00:00:03` | `3` (`s1-eth3`) |

* **Interfaces del Router (Controlador):**
  * **Interfaz Privada (Gateway):** `10.0.0.1` (`00:00:00:00:01:01`)
  * **Interfaz Pública (NAT IP):** `200.0.0.1` (`00:00:00:00:01:02`)
* **Características de red:** Ancho de banda de `100 Mbps`, retardo de `5 ms` por enlace y sin entradas ARP estáticas precargadas (`autoStaticArp=False`).

---

## 🚀 Ejecución

Para levantar el entorno correctamente, iniciá primero el controlador y luego la topología en **dos terminales distintas**.

### 1. Iniciar el Controlador POX

Copiá los archivos de `controlador/` dentro del directorio `ext/` de tu instalación de POX (o agregalos al `PYTHONPATH`) y ejecutá:

```bash
./pox.py log.level --DEBUG protorouter
```

### 2. Iniciar la Topología en Mininet

En una segunda terminal, ejecutá el script de topología con privilegios de superusuario:

```bash
sudo python3 topologia/topo.py
```

---

## 🧪 Pruebas y Validación

Desde la CLI de Mininet (`mininet>`), podés verificar el funcionamiento de PAT con los siguientes escenarios:

### 🔹 Escenario 1: Tráfico TCP (`iperf` / `netcat`)
1. Iniciar un servidor TCP en el host público (`h3`):
```bash
mininet> h3 iperf -s -p 5001 &
```
2. Iniciar clientes desde los hosts privados (`h1` y `h2`):
```bash
mininet> h1 iperf -c 200.0.0.100 -p 5001 -t 5
mininet> h2 iperf -c 200.0.0.100 -p 5001 -t 5
```

### 🔹 Escenario 2: Tráfico UDP
1. Iniciar un servidor UDP en `h3`:
```bash
mininet> h3 iperf -s -u -p 6001 &
```
2. Enviar datagramas desde `h1` y `h2`:
```bash
mininet> h1 iperf -c 200.0.0.100 -u -p 6001 -t 5
mininet> h2 iperf -c 200.0.0.100 -u -p 6001 -t 5
```

### 🔹 Escenario 3: Concurrencia y Expiración de Sesiones
* Ejecutá transferencias simultáneas desde `h1` y `h2` hacia `h3` para comprobar la asignación única de puertos públicos en la tabla PAT.
* Tras **30 segundos** de inactividad (`IDLE_TIMEOUT = 30`), las reglas en el switch y las entradas en la tabla de traducción expiran automáticamente.

---

## 🛠️ Configuración y Extensión

* **Constantes principales** (definidas en `controlador/protorouter.py` y `controlador/flujos.py`):
  * Rango de puertos PAT asignables: `1024` a `65535`
  * Tiempo de expiración por inactividad (`IDLE_TIMEOUT`): `30` segundos
* **Agregar nuevos hosts privados:**
  1. Instanciar el nuevo host en `topologia/topo.py` dentro de la subred `10.0.0.0/24` con gateway `10.0.0.1`.
  2. Registrar su dirección IP, MAC y número de puerto en la estructura `CONFIG_PUERTOS` de `controlador/protorouter.py`.
* **Limpieza del entorno Mininet:**
  Si ocurre un cierre inesperado, limpiá las interfaces residuales ejecutando:
```bash
sudo mn -c
```
