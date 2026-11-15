"""Envía un archivo por el mini-Internet, una línea por paquete IP.

Uso: python3 prueba_router.py headers IP_router_inicial puerto_router_inicial [archivo]
     ej: python3 prueba_router.py "127.0.0.1;8885;10" 127.0.0.1 8881 < archivo.txt

headers es "IP;puerto;TTL", los headers de cada paquete: la dirección del router final y el TTL. Va
entre comillas porque la shell interpreta ; como separador de comandos. Lee el archivo indicado o,
si no se indica, la entrada estándar, y envía cada línea, sin su salto de línea, en un paquete
distinto a (IP_router_inicial, puerto_router_inicial). Los paquetes salen seguidos, sin pausas.
"""
import socket
import sys

from router import address_str, create_packet

if len(sys.argv) not in (4, 5):
    sys.exit('Uso: python3 prueba_router.py "IP;puerto;TTL" IP_router_inicial puerto_router_inicial [archivo]')

try:
    headers = sys.argv[1].split(";")
    if len(headers) != 3:
        raise ValueError(f"los headers deben tener la forma IP;puerto;TTL, no {sys.argv[1]!r}")
    destination_ip, destination_port, ttl = headers[0], int(headers[1]), int(headers[2])
    first_router = (sys.argv[2], int(sys.argv[3]))
    create_packet({"ip": destination_ip, "port": destination_port, "ttl": ttl, "message": b""})  # valida los headers
    input_file = open(sys.argv[4], "rb") if len(sys.argv) == 5 else sys.stdin.buffer
except (OSError, ValueError) as error:
    sys.exit(f"Error: {error}")

sent = 0
with input_file, socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as send_socket:
    for line in input_file:  # en bytes: el mensaje del paquete es la línea tal como está en el archivo
        IP_packet = create_packet({"ip": destination_ip, "port": destination_port, "ttl": ttl,
                                   "message": line.rstrip(b"\r\n")})
        send_socket.sendto(IP_packet, first_router)
        sent += 1
print(f"Se enviaron {sent} paquetes con destino {destination_ip}:{destination_port} y TTL {ttl} a "
      f"{address_str(first_router)}", file=sys.stderr)
