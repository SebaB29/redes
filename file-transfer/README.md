# TP1 - File Transfer (Redes TA048)

Aplicación cliente-servidor de transferencia de archivos sobre UDP, con transferencia confiable implementada a nivel de aplicación mediante dos protocolos de recuperación de errores:

- **Stop & Wait**
- **Selective Repeat**

Operaciones soportadas:

- **UPLOAD**: el cliente envía un archivo al servidor.
- **DOWNLOAD**: el cliente descarga un archivo del servidor.

## Integrantes

Brizuela Sebastian 105288
Fraga Fernando 102369
Ricardo Tomas Dopacio 111097
Colazo Sebastian 111737
Guttlein Gareis Alexis 104431

## Requisitos

- Python 3
- [Mininet](http://mininet.org/) para la topología simulada.
- `flake8` para verificar el estilo: `pip install flake8`.
- Wireshark para analizar el tráfico.

## Estructura del proyecto

```
.
├── informe.pdf
├── README.md
└── src/
    ├── lib/              # módulos compartidos (protocolo, sockets, etc.)
    ├── start-server      # servidor
    ├── upload            # cliente: subir archivo
    └── download          # cliente: descargar archivo
```

## Uso

Todos los comandos se ejecutan desde la raíz del proyecto.

### Servidor

```bash
python3 src/start-server [-h] [-v | -q] [-H ADDR] [-p PORT] [-s DIRPATH]
```

| Opción | Descripción |
|---|---|
| `-h`, `--help` | Muestra la ayuda |
| `-v`, `--verbose` | Aumenta la salida por consola |
| `-q`, `--quiet` | Reduce la salida por consola |
| `-H`, `--host` | IP del servidor |
| `-p`, `--port` | Puerto del servidor |
| `-s`, `--storage` | Directorio donde se guardan los archivos |

Ejemplo:

```bash
mkdir -p /tmp/storage
python3 src/start-server -v -H 10.0.0.1 -p 5000 -s /tmp/storage
```

### Cliente: upload

```bash
python3 src/upload [-h] [-v | -q] [-H ADDR] [-p PORT] [-s FILEPATH] [-n FILENAME] [-r protocol]
```

| Opción | Descripción |
|---|---|
| `-H`, `--host` | IP del servidor |
| `-p`, `--port` | Puerto del servidor |
| `-s`, `--src` | Ruta del archivo local a subir |
| `-n`, `--name` | Nombre con el que se guarda en el servidor |
| `-r`, `--protocol` | Protocolo de recuperación de errores: stop-and-wait  o selective-repeat |

Ejemplo:

```bash
python3 src/upload -v -H 10.0.0.1 -p 5000 -s /tmp/archivo.bin -n archivo.bin -r sr
```

### Cliente: download

```bash
python3 src/download [-h] [-v | -q] [-H ADDR] [-p PORT] [-d FILEPATH] [-n FILENAME] [-r protocol]
```

| Opción | Descripción |
|---|---|
| `-H`, `--host` | IP del servidor |
| `-p`, `--port` | Puerto del servidor |
| `-d`, `--dst` | Ruta local donde se guarda el archivo descargado |
| `-n`, `--name` | Nombre del archivo en el servidor |
| `-r`, `--protocol` | Protocolo de recuperación de errores: stop-and-wait  o selective-repeat |

Ejemplo:

```bash
python3 src/download -v -H 10.0.0.1 -p 5000 -d /tmp/descargado.bin -n archivo.bin -r sr
```

## Ejecución con Mininet

### Levantar la topología

Un switch y 5 hosts (h1 servidor, h2 a h5 clientes), con 10 % de pérdida por sentido y RTT de 40 ms:

```bash
sudo mn -c
sudo mn -x --topo single,2 --link tc,loss=10,delay=10ms
```

- `loss=10` por enlace da 10 % de pérdida por sentido en el camino de 2 enlaces.
- `delay=10ms` por enlace da un RTT de aproximadamente 40 ms.
- Para un RTT de 300 ms: `delay=75ms`.
- `-x` abre una terminal por cada nodo (`h1`, `h2`, ...). Los comandos del TP se ejecutan en las terminales de los hosts.

### Verificar la red

En la terminal de h2:

```bash
ping -c 100 -i 0.2 10.0.0.1
```

Se espera un RTT mínimo cercano a 40 ms y alrededor de 19 % de pérdida (el ping cuenta ida y vuelta).


### Concurrencia

Desde distintos hosts, lanzar en simultáneo (cada uno con un nombre de archivo de destino distinto):

```bash
# h2 y h3: uploads
python3 src/upload -v -H 10.0.0.1 -p 5000 -s /tmp/1mb.bin -n up_h2.bin -r sr
python3 src/upload -v -H 10.0.0.1 -p 5000 -s /tmp/1mb.bin -n up_h3.bin -r saw

# h4 y h5: downloads (el archivo debe existir en el servidor)
python3 src/download -v -H 10.0.0.1 -p 5000 -d /tmp/down/d4.bin -n prueba.bin -r sr
python3 src/download -v -H 10.0.0.1 -p 5000 -d /tmp/down/d5.bin -n prueba.bin -r saw
```

## Manejo de errores

- Descarga de un archivo inexistente en el servidor: Se le notifica al cliente que no existe tal archivo y corta su proceso, mientras que el servidor sigue escuchando.
- Archivo fuente inexistente en el cliente: Se le notifica al cliente que no existe tal archivo y corta su proceso, mientras que el servidor sigue escuchando.

## Estilo de código

El código sigue PEP 8. Para verificarlo:

```bash
flake8 src/
```

## Limpieza

Si Mininet quedó con procesos o interfaces de una corrida anterior:

```bash
sudo mn -c
```
