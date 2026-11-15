"""Router del mini-Internet de la actividad Forwarding básico (CC4303).

Uso: python3 router.py router_IP router_puerto router_rutas.txt

El router escucha en (router_IP, router_puerto) paquetes IP simulados que llegan por UDP. Descarta
los que llegan con TTL 0. Si un paquete va dirigido a él, imprime su mensaje; si no, busca el
siguiente salto en su tabla de rutas y se lo reenvía con el TTL disminuido en 1.
"""
import ipaddress
import socket
import sys
from typing import NamedTuple, Optional

# Formato del paquete IP, solo bytes:
#   [0:4] IP de destino: un byte por cada número de a.b.c.d
#   [4:6] puerto de destino: entero sin signo de 2 bytes, big-endian
#   [6]   TTL: entero sin signo de 1 byte
#   [7:9] ID del datagrama: entero sin signo de 2 bytes, big-endian
#   [9:13] offset del fragmento: entero sin signo de 4 bytes, big-endian
#   [13:17] tamaño del mensaje: entero sin signo de 4 bytes, big-endian
#   [17] FLAG: 1 si quedan fragmentos, 0 si es el último
#   [18:] mensaje
HEADER_SIZE = 18
BUFFER_SIZE = 65535  # cabe cualquier datagrama UDP


def parse_packet(IP_packet: bytes) -> dict:
    """Convierte un paquete IP en un dict con las llaves ip (str a.b.c.d), port (int), ttl (int), 
    id (int), offset (int), size (int), flag (int) y message (bytes, sin headers). Lanza ValueError si el paquete es más corto que el header."""
    if len(IP_packet) < HEADER_SIZE:
        raise ValueError(f"el paquete tiene {len(IP_packet)} bytes y el header ocupa {HEADER_SIZE}")
    size = int.from_bytes(IP_packet[13:17], "big")
    message = bytes(IP_packet[HEADER_SIZE:])
    flag = IP_packet[17]
    if flag not in (0, 1):
        raise ValueError(f"FLAG fuera de rango: {flag}")
    if size != len(message):
        raise ValueError(f"el tamaño declarado es {size}, pero el mensaje ocupa {len(message)} bytes")
    return {"ip": str(ipaddress.IPv4Address(bytes(IP_packet[0:4]))),
            "port": int.from_bytes(IP_packet[4:6], "big"),
            "ttl": IP_packet[6],
            "id": int.from_bytes(IP_packet[7:9], "big"),
            "offset": int.from_bytes(IP_packet[9:13], "big"),
            "size": size,
            "flag": flag,
            "message": message}


def create_packet(parsed_IP_packet: dict) -> bytes:
    """Inversa de parse_packet: arma el paquete IP en bytes a partir del dict. message puede ser
    bytes o str, que se codifica en UTF-8. Lanza ValueError si algún campo no cabe en el header."""
    ip = ipaddress.IPv4Address(parsed_IP_packet["ip"]).packed
    port = parsed_IP_packet["port"]
    ttl = parsed_IP_packet["ttl"]
    datagram_id = parsed_IP_packet.get("id", 0)
    offset = parsed_IP_packet.get("offset", 0)
    flag = parsed_IP_packet.get("flag", 0)
    if not 0 <= port <= 0xFFFF:
        raise ValueError(f"puerto fuera de rango: {port}")
    if not 0 <= ttl <= 0xFF:
        raise ValueError(f"TTL fuera de rango: {ttl}")
    if not 0 <= datagram_id <= 0xFFFF:
        raise ValueError(f"ID fuera de rango: {datagram_id}")
    if not 0 <= offset <= 0xFFFFFFFF:
        raise ValueError(f"offset fuera de rango: {offset}")
    if flag not in (0, 1):
        raise ValueError(f"FLAG fuera de rango: {flag}")
    message = parsed_IP_packet["message"]
    if isinstance(message, str):
        message = message.encode()
    size = len(message)
    if "size" in parsed_IP_packet and parsed_IP_packet["size"] != size:
        raise ValueError(f"el tamaño declarado es {parsed_IP_packet['size']}, pero el mensaje ocupa {size} bytes")
    if size > 0xFFFFFFFF:
        raise ValueError(f"mensaje demasiado grande: {size} bytes")
    return (ip + port.to_bytes(2, "big") + ttl.to_bytes(1, "big") +
            datagram_id.to_bytes(2, "big") + offset.to_bytes(4, "big") +
            size.to_bytes(4, "big") + flag.to_bytes(1, "big") + message)


def address_str(address) -> str:
    """Dirección (IP, puerto) como texto, ej: 127.0.0.1:8881."""
    return f"{address[0]}:{address[1]}"


def describe(parsed_IP_packet: dict) -> str:
    """Paquete legible para los mensajes del router, ej: [127.0.0.1:8885, TTL=10, 'hola']. En el
    socket el paquete viaja en bytes; esto es solo para mostrarlo."""
    message = parsed_IP_packet["message"].decode(errors="replace")
    return (f"[{parsed_IP_packet['ip']}:{parsed_IP_packet['port']}, TTL={parsed_IP_packet['ttl']}, "
            f"{message!r}]")


class Route(NamedTuple):
    """Una línea de la tabla de rutas."""
    network: ipaddress.IPv4Network  # red de destino
    first_port: int                 # rango de puertos de destino, ambos extremos incluidos
    last_port: int
    next_hop: tuple                 # (IP, puerto) del siguiente salto
    mtu: int

    @property
    def area(self) -> tuple:
        """Área de la red a la que lleva la ruta. Las líneas con la misma área son rutas
        alternativas hacia ella."""
        return (self.network, self.first_port, self.last_port)

    def matches(self, address) -> bool:
        ip, port = address
        return ipaddress.IPv4Address(ip) in self.network and self.first_port <= port <= self.last_port


def read_routes(routes_file_name: str) -> list:
    """Lee una tabla de rutas. Cada línea tiene la forma
        [Red (CIDR)] [Puerto_Inicial] [Puerto_final] [IP_Para_llegar] [Puerto_para_llegar]
    Se ignoran las líneas vacías, las que empiezan con # y las columnas sobrantes."""
    routes = []
    with open(routes_file_name, encoding="utf-8") as routes_file:
        for line_number, line in enumerate(routes_file, start=1):
            fields = line.split()
            if not fields or fields[0].startswith("#"):
                continue
            try:
                network, first_port, last_port, hop_ip, hop_port = fields[:5]
                mtu = int(fields[5]) if len(fields) > 5 else 1500
                routes.append(Route(ipaddress.IPv4Network(network, strict=False),  # 127.0.0.1/24 es 127.0.0.0/24
                                    int(first_port), int(last_port),
                                    (str(ipaddress.IPv4Address(hop_ip)), int(hop_port)), mtu))
            except ValueError as error:
                raise ValueError(f"{routes_file_name}, línea {line_number} ({line.strip()!r}): {error}") from None
    return routes


# Estado de round-robin. Para cada par (tabla de rutas, área) guarda la posición, entre las rutas
# alternativas hacia esa área, de la próxima que se usará. Cada área tiene su propia cuenta.
round_robin_state = {}


def check_routes(routes_file_name: str, destination_address: tuple) -> Optional[tuple]:
    """Retorna ((IP, puerto), MTU) del siguiente salto hacia destination_address,
    o None si ninguna ruta sirve. Recorre la tabla en orden, y la primera línea
    que calza define el área de destino: su red y su rango de puertos. Si varias
    líneas llevan a esa misma área, se alternan con round-robin."""
    routes = read_routes(routes_file_name)
    for route in routes:
        if route.matches(destination_address):
            alternatives = [other for other in routes if other.area == route.area]
            key = (routes_file_name, route.area)
            position = round_robin_state.get(key, 0) % len(alternatives)
            round_robin_state[key] = (position + 1) % len(alternatives)
            selected = alternatives[position]
            return selected.next_hop, selected.mtu
    return None


def handle_packet(router_socket, router_address, routes_file_name, IP_packet):
    """Procesa un paquete recibido. Si llega con TTL 0 lo descarta, aunque vaya dirigido a este
    router. Si no, imprime su mensaje si es para este router, o lo reenvía con el TTL disminuido en
    1 al siguiente salto que entrega check_routes."""
    try:
        packet = parse_packet(IP_packet)
    except ValueError as error:
        print(f"Se descarta un paquete inválido ({error}): {IP_packet!r}")
        return
    if packet["ttl"] == 0:
        print(f"Se recibió paquete {describe(packet)} con TTL 0")
        return
    destination_address = (packet["ip"], packet["port"])
    if destination_address == router_address:
        print(packet["message"].decode(errors="replace"))
        return
    try:
        route = check_routes(routes_file_name, destination_address)
    except (OSError, ValueError) as error:
        print(f"No se pudo leer la tabla de rutas ({error}); se descarta el paquete {describe(packet)}")
        return
    if route is None:
        print(f"No hay rutas hacia {address_str(destination_address)} para paquete {describe(packet)}")
        return
    next_hop, mtu = route
    packet["ttl"] -= 1  # el mensaje muestra el paquete tal como se reenvía
    print(f"redirigiendo paquete {describe(packet)} con destino final {address_str(destination_address)} "
          f"desde {address_str(router_address)} hacia {address_str(next_hop)}")
    try:
        router_socket.sendto(create_packet(packet), next_hop)
    except OSError as error:  # por ejemplo, un siguiente salto inalcanzable
        print(f"No se pudo reenviar el paquete a {address_str(next_hop)} ({error})")


def main():
    if len(sys.argv) != 4:
        sys.exit("Uso: python3 router.py router_IP router_puerto router_rutas.txt")
    try:
        # La IP queda normalizada para compararla con la de destino que sale de parse_packet
        router_address = (str(ipaddress.IPv4Address(sys.argv[1])), int(sys.argv[2]))
        if not 0 < router_address[1] <= 0xFFFF:
            raise ValueError(f"puerto fuera de rango: {router_address[1]}")
        routes = read_routes(sys.argv[3])  # una tabla inexistente o con errores se detecta al partir
    except (OSError, ValueError) as error:
        sys.exit(f"Error: {error}")
    routes_file_name = sys.argv[3]
    sys.stdout.reconfigure(line_buffering=True)  # cada línea aparece de inmediato, también en un pipe

    router_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        router_socket.bind(router_address)  # sin timeout, así que recvfrom es bloqueante
    except OSError as error:
        sys.exit(f"Error: no se puede escuchar en {address_str(router_address)} ({error})")
    print(f"Router {address_str(router_address)} escuchando, tabla de rutas {routes_file_name} "
          f"({len(routes)} {'ruta' if len(routes) == 1 else 'rutas'})")
    try:
        while True:
            try:
                IP_packet, _ = router_socket.recvfrom(BUFFER_SIZE)
            except ConnectionResetError:
                continue  # Windows avisa así que un envío anterior no llegó a destino; se ignora
            handle_packet(router_socket, router_address, routes_file_name, IP_packet)
    except KeyboardInterrupt:
        pass
    finally:
        router_socket.close()


if __name__ == "__main__":
    main()
