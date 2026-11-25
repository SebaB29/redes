# 📁 File Transfer

> Aplicación cliente-servidor de transferencia confiable de archivos sobre **UDP**, implementando protocolos de recuperación de errores a nivel de aplicación (**Stop & Wait** y **Selective Repeat**).

---

## ✨ Operaciones Soportadas

* **📤 UPLOAD:** El cliente envía un archivo local hacia el servidor para su almacenamiento.
* **📥 DOWNLOAD:** El cliente solicita y descarga un archivo almacenado en el servidor.

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

## 🛠️ Requisitos

| Herramienta | Propósito / Instalación |
| :--- | :--- |
| **Python 3** | Entorno de ejecución de cliente y servidor |
| **[Mininet](http://mininet.org/)** | Simulación de topologías y condiciones de red (pérdida y delay) |
| **`flake8`** | Verificación de estilo de código (`pip install flake8`) |
| **Wireshark** | Captura y análisis de paquetes UDP en la red |

---

## 📂 Estructura del Proyecto

```text
.
├── informe.pdf
├── README.md
└── src/
    ├── lib/              # Módulos compartidos (protocolo, sockets, etc.)
    ├── start-server      # Servidor principal
    ├── upload            # Cliente: subir archivo
    └── download          # Cliente: descargar archivo
```

---

## 🚀 Uso

Todos los comandos se ejecutan desde la raíz del proyecto.

### 🖥️ Servidor

```bash
python3 src/start-server [-h] [-v | -q] [-H ADDR] [-p PORT] [-s DIRPATH]
```

| Opción | Descripción |
| :--- | :--- |
| `-h`, `--help` | Muestra la ayuda |
| `-v`, `--verbose` | Aumenta la salida por consola |
| `-q`, `--quiet` | Reduce la salida por consola |
| `-H`, `--host` | IP del servidor |
| `-p`, `--port` | Puerto del servidor |
| `-s`, `--storage` | Directorio donde se guardan los archivos |

**Ejemplo:**

```bash
mkdir -p /tmp/storage
python3 src/start-server -v -H 10.0.0.1 -p 5000 -s /tmp/storage
```

---

### 📤 Cliente: Upload

```bash
python3 src/upload [-h] [-v | -q] [-H ADDR] [-p PORT] [-s FILEPATH] [-n FILENAME] [-r protocol]
```

| Opción | Descripción |
| :--- | :--- |
| `-H`, `--host` | IP del servidor |
| `-p`, `--port` | Puerto del servidor |
| `-s`, `--src` | Ruta del archivo local a subir |
| `-n`, `--name` | Nombre con el que se guarda en el servidor |
| `-r`, `--protocol` | Protocolo de recuperación de errores: `stop-and-wait` o `selective-repeat` |

**Ejemplo:**

```bash
python3 src/upload -v -H 10.0.0.1 -p 5000 -s /tmp/archivo.bin -n archivo.bin -r sr
```

---

### 📥 Cliente: Download

```bash
python3 src/download [-h] [-v | -q] [-H ADDR] [-p PORT] [-d FILEPATH] [-n FILENAME] [-r protocol]
```

| Opción | Descripción |
| :--- | :--- |
| `-H`, `--host` | IP del servidor |
| `-p`, `--port` | Puerto del servidor |
| `-d`, `--dst` | Ruta local donde se guarda el archivo descargado |
| `-n`, `--name` | Nombre del archivo en el servidor |
| `-r`, `--protocol` | Protocolo de recuperación de errores: `stop-and-wait` o `selective-repeat` |

**Ejemplo:**

```bash
python3 src/download -v -H 10.0.0.1 -p 5000 -d /tmp/descargado.bin -n archivo.bin -r sr
```

---

## 🌐 Ejecución con Mininet

### 1. Levantar la topología

Un switch y 5 hosts (`h1` servidor, `h2` a `h5` clientes), con 10 % de pérdida por sentido y RTT de 40 ms:

```bash
sudo mn -c
sudo mn -x --topo single,2 --link tc,loss=10,delay=10ms
```

* `loss=10` por enlace da **10 % de pérdida por sentido** en el camino de 2 enlaces.
* `delay=10ms` por enlace da un **RTT de aproximadamente 40 ms**.
* Para un **RTT de 300 ms**: utilizar `delay=75ms`.
* `-x` abre una terminal por cada nodo (`h1`, `h2`, ...). Los comandos del TP se ejecutan en las terminales de los hosts.

### 2. Verificar la red

En la terminal de `h2`:

```bash
ping -c 100 -i 0.2 10.0.0.1
```

> Se espera un RTT mínimo cercano a **40 ms** y alrededor de **19 % de pérdida** (el `ping` cuenta ida y vuelta).

### 3. Concurrencia

Desde distintos hosts, lanzar en simultáneo (cada uno con un nombre de archivo de destino distinto):

```bash
# h2 y h3: uploads
python3 src/upload -v -H 10.0.0.1 -p 5000 -s /tmp/1mb.bin -n up_h2.bin -r sr
python3 src/upload -v -H 10.0.0.1 -p 5000 -s /tmp/1mb.bin -n up_h3.bin -r saw

# h4 y h5: downloads (el archivo debe existir en el servidor)
python3 src/download -v -H 10.0.0.1 -p 5000 -d /tmp/down/d4.bin -n prueba.bin -r sr
python3 src/download -v -H 10.0.0.1 -p 5000 -d /tmp/down/d5.bin -n prueba.bin -r saw
```

---

## ⚠️ Manejo de Errores

* **Descarga de un archivo inexistente en el servidor:** Se le notifica al cliente que no existe tal archivo y corta su proceso, mientras que el servidor sigue escuchando.
* **Archivo fuente inexistente en el cliente:** Se le notifica al cliente que no existe tal archivo y corta su proceso, mientras que el servidor sigue escuchando.

---

## 🧹 Estilo de Código y Limpieza

### Verificar estilo (PEP 8)

```bash
flake8 src/
```

### Limpiar entorno de Mininet

Si Mininet quedó con procesos o interfaces de una corrida anterior[cite: 28]:

```bash
sudo mn -c
```
