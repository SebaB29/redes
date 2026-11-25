# TP2 - SDN / NAT (Redes TA048)
 
Router SDN con **NAT saliente y traducción por puertos (PAT)** implementado como controlador POX sobre un switch OpenFlow emulado en Mininet. Varios hosts de una red privada comparten una única IP pública para comunicarse con un servidor de la red pública.
 
Funcionalidades:
 
- **ARP dinámico**: el controlador responde los ARP Requests dirigidos al router y genera ARP Requests para resolver la MAC del servidor público. No hay entradas ARP estáticas en ningún host.
- **PAT (TCP y UDP)**: tablas de traducción `(ip, puerto, protocolo) <-> puerto público`, con puertos asignados dinámicamente.
- **Instalación reactiva de flujos**: el controlador instala una regla saliente y una entrante por conexión, y el resto del tráfico lo procesa el switch.
- **Liberación por inactividad**: las reglas expiran por `idle_timeout` y el controlador libera el puerto público al recibir `FlowRemoved`.
 
## Requisitos
 
- Python 3
- [Mininet](http://mininet.org/) (incluye Open vSwitch)
- POX (ya incluido en este repositorio, en `pox/`)
- `iperf` para generar tráfico de prueba
- Wireshark o `tcpdump` para analizar el tráfico (opcional)
 
## Topología
 
Un switch `s1` que actúa como router con dos interfaces, un servidor en la red pública y dos hosts en la red privada:
 
| Elemento | IP | MAC | Puerto de `s1` |
|---|---|---|---|
| `h1` (servidor) | 200.0.0.1/24 | 00:00:00:00:00:01 | 1 |
| Interfaz pública del router | 200.0.0.254 | 00:00:00:aa:aa:aa | 1 |
| Interfaz privada del router | 192.168.1.254 | 00:00:00:bb:bb:bb | -- |
| `h2` | 192.168.1.2/24 | 00:00:00:00:00:02 | 2 |
| `h3` | 192.168.1.3/24 | 00:00:00:00:00:03 | 3 |
 
El puerto 1 de `s1` es el público: `h1` debe ser siempre el primer enlace que se agrega en `topo.py`.
 
## Uso
 
Todos los comandos se ejecutan desde la raíz del proyecto, en dos terminales distintas.
 
### 1. Controlador
 
```bash
python3 pox/pox.py log.level --DEBUG protorouter
```
 
### 2. Topología
 
```bash
sudo python3 topo.py
```
 
Abre la CLI de Mininet. Verificar en la terminal del controlador que el switch se conectó (`Iniciando ProtoRouter para Switch ...`).
 
El orden recomendado es iniciar primero el controlador y después la topología.
 
## Pruebas
 
Los comandos se escriben en la CLI de Mininet. Si se prefiere una terminal por nodo: `xterm h1 h2 h3`.
 
> **Nota:** el NAT traduce solo TCP y UDP, por lo que `ping` desde la red privada no funciona. Para probar usar `iperf`.
 
### Conectividad básica (TCP)
 
```bash
h1 iperf -s &
h2 iperf -c 200.0.0.1
```
 
### UDP
 
```bash
h1 iperf -s -u &
h2 iperf -c 200.0.0.1 -u -b 1M -l 512
```
 
### Concurrencia
 
Desde distintos hosts, en simultáneo:
 
```bash
h2 iperf -c 200.0.0.1 -t 20 &
h3 iperf -c 200.0.0.1 -t 20 &
```
 
El servidor registra ambas conexiones desde `200.0.0.254` con puertos distintos.

## Configuración
 
No hay argumentos de línea de comandos: los valores del router son constantes al inicio de los módulos y deben mantenerse iguales en ambos.
 
| Constante | Valor | Archivo |
|---|---|---|
| `PRIVATE_SUBNET` / `PRIVATE_MASK` | 192.168.1.0 / 24 | `protorouter.py` |
| `PRIVATE_IP` | 192.168.1.254 | `protorouter.py` |
| `PUBLIC_IP` | 200.0.0.254 | `protorouter.py` |
| `PRIVATE_MAC` | 00:00:00:bb:bb:bb | `protorouter.py`, `flujos.py` |
| `PUBLIC_MAC` | 00:00:00:aa:aa:aa | `protorouter.py`, `flujos.py` |
| `PUBLIC_PORT` | 1 | `protorouter.py`, `flujos.py` |
| `NAT_PORT_MIN` / `NAT_PORT_MAX` | 20000 / 40000 | `protorouter.py` |
| `idle_timeout` | 50 s | `flujos.py` |
 
Las IP y MAC de los hosts no están fijadas en el controlador: se pueden cambiar en `topo.py`.
 
### Agregar un host privado
 
En `NATTopo.build()` de `topo.py`, antes de los `addLink` de los hosts:
 
```python
h4 = self.addHost('h4', ip='192.168.1.4/24', mac='00:00:00:00:00:04',
                  defaultRoute='via 192.168.1.254')
self.addLink(h4, s1)
```
 
El controlador toma la MAC y el puerto del switch del primer paquete del host, por lo que no requiere cambios.
 
## Limpieza
 
Si Mininet quedó con procesos o interfaces de una corrida anterior:
 
```bash
sudo mn -c
```
 
