"""Envía un mensaje por el mini-Internet.

Uso: python3 enviar.py IP_router_final puerto_router_final mensaje IP_envío puerto_envío [TTL]

Arma un paquete IP con destino (IP_router_final, puerto_router_final), el TTL dado (64 por omisión,
como en Linux) y el mensaje, y lo envía por UDP a (IP_envío, puerto_envío), el router por donde el
paquete entra a la red. El mensaje va entre comillas si tiene espacios.
"""
import socket
import sys

from router import address_str, create_packet

DEFAULT_TTL = 64

if len(sys.argv) not in (6, 7):
    sys.exit("Uso: python3 enviar.py IP_router_final puerto_router_final mensaje IP_envío puerto_envío [TTL]")

try:
    destination_address = (sys.argv[1], int(sys.argv[2]))
    send_address = (sys.argv[4], int(sys.argv[5]))
    ttl = int(sys.argv[6]) if len(sys.argv) == 7 else DEFAULT_TTL
    IP_packet = create_packet({"ip": destination_address[0], "port": destination_address[1], "ttl": ttl,
                               "message": sys.argv[3]})
except ValueError as error:
    sys.exit(f"Error: {error}")

with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as send_socket:
    send_socket.sendto(IP_packet, send_address)
print(f"Paquete de {len(IP_packet)} bytes con destino {address_str(destination_address)} y TTL {ttl} "
      f"enviado a {address_str(send_address)}", file=sys.stderr)
