"""Pruebas de parse_packet, create_packet, check_routes y del manejo del TTL, sin levantar routers.

Uso: python3 pruebas/test_funciones.py

Verifica el resultado esperado de las pruebas de las actividades 5 y 6. Termina con error en la primera prueba que falla.
"""
import contextlib
import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from router import (check_routes, create_packet, fragment_IP_packet, handle_packet, parse_packet,
                    received_packets, reassemble_IP_packet, round_robin_state)  # noqa: E402


def routes(name):
    return str(ROOT / "rutas" / name)


def check(description, result, expected):
    print(f"{description} -> {result}")
    assert result == expected, f"se esperaba {expected}"


def expect_value_error(description, function, argument):
    try:
        function(argument)
    except ValueError as error:
        print(f"{description} -> ValueError: {error}")
    else:
        raise AssertionError(f"{description} no lanzó ValueError")

# ==================================================
# ACTIVIDAD 5: Forwarding básico
# ==================================================

print("== Parse y create (paso 4 de la parte I, con el TTL del paso 1 de la parte II y fragmentación (act 6))")
IP_packet_v1 = (bytes([127, 0, 0, 1]) + (8885).to_bytes(2, "big") + bytes([10]) +
                (42).to_bytes(2, "big") + (3).to_bytes(4, "big") +
                (4).to_bytes(4, "big") + bytes([1]) + b"hola")

parsed_IP_packet = parse_packet(IP_packet_v1)
IP_packet_v2 = create_packet(parsed_IP_packet)
print(f"IP_packet_v1 = {IP_packet_v1!r}")
print(f"parse_packet(IP_packet_v1) = {parsed_IP_packet}")
print("IP_packet_v1 == IP_packet_v2 ? {}".format(IP_packet_v1 == IP_packet_v2))
assert IP_packet_v1 == IP_packet_v2
assert parsed_IP_packet == {"ip": "127.0.0.1", "port": 8885, "ttl": 10, "id": 42, "offset": 3,
                            "size": 4, "flag": 1, "message": b"hola"}
check("create_packet de 192.168.0.10:443 con header de fragmentación y mensaje 'ñandú'",
      create_packet({"ip": "192.168.0.10", "port": 443, "ttl": 255, "id": 7, "offset": 0,
                     "flag": 0, "message": "ñandú"}),
      b"\xc0\xa8\x00\x0a\x01\xbb\xff\x00\x07\x00\x00\x00\x00\x00\x00\x00\x07\x00" +
      "ñandú".encode())
expect_value_error("parse_packet(b'')", parse_packet, b"")
expect_value_error("parse_packet de un header truncado", parse_packet, b"\x7f\x00\x00\x01\x22\xb5")
expect_value_error("parse_packet con tamaño declarado incorrecto", parse_packet, IP_packet_v1[:-1])
expect_value_error("create_packet con TTL 256", create_packet,
                   {"ip": "127.0.0.1", "port": 8885, "ttl": 256, "message": b""})
expect_value_error("create_packet con puerto 70000", create_packet,
                   {"ip": "127.0.0.1", "port": 70000, "ttl": 10, "message": b""})
expect_value_error("create_packet con FLAG 2", create_packet,
                   {"ip": "127.0.0.1", "port": 8885, "ttl": 10, "flag": 2, "message": b""})

print("\n== Paso 6: check_routes con las tablas del ejemplo 2 (R1 - R2 - R3)")
for table, destination, expected in [
        ("rutas_R1_v2.txt", ("127.0.0.1", 8882), (("127.0.0.1", 8882), 1500)),
        ("rutas_R1_v2.txt", ("127.0.0.1", 8883), (("127.0.0.1", 8882), 1500)),
        ("rutas_R2_v2.txt", ("127.0.0.1", 8881), (("127.0.0.1", 8881), 1500)),
        ("rutas_R2_v2.txt", ("127.0.0.1", 8883), (("127.0.0.1", 8883), 1500)),
        ("rutas_R3_v2.txt", ("127.0.0.1", 8881), (("127.0.0.1", 8882), 1500)),
        ("rutas_R1_v2.txt", ("127.0.0.1", 8884), None),   # puerto fuera de la red
        ("rutas_R2_v2.txt", ("127.0.0.1", 8884), None),
        ("rutas_R1_v2.txt", ("10.0.0.1", 8883), None)]:   # IP fuera de 127.0.0.0/24
    check(f"check_routes({table}, {destination})", check_routes(routes(table), destination), expected)

print("\n== Paso 8: round-robin en R2 de la red de 5 routers")
hops = [check_routes(routes("rutas_R2_v3.txt"), ("127.0.0.1", 8885))[0][1] for _ in range(6)]
check("6 consultas hacia 127.0.0.1:8885", hops, [8883, 8884] * 3)
check("hacia 127.0.0.1:8881 (una sola ruta)",
      [check_routes(routes("rutas_R2_v3.txt"), ("127.0.0.1", 8881))[0][1] for _ in range(3)], [8881] * 3)

print("\n== Paso 8: round-robin por área en R2 de la red de 7 routers, consultas intercaladas")
to_R5, to_R1 = [], []
for _ in range(6):
    to_R5.append(check_routes(routes("rutas_R2_v4.txt"), ("127.0.0.1", 8885))[0][1])
    to_R1.append(check_routes(routes("rutas_R2_v4.txt"), ("127.0.0.1", 8881))[0][1])
check("hacia 127.0.0.1:8885 (área 8883-8886)", to_R5, [8883, 8884, 8886] * 2)
check("hacia 127.0.0.1:8881 (área 8880-8881)", to_R1, [8881, 8880] * 3)

print("\n== Paso 9: ruta default en la última línea")
for table, destination, expected in [
        ("rutas_R2_v5.txt", ("127.0.0.1", 8881), (("127.0.0.1", 8881), 1500)),
        ("rutas_R1_v5.txt", ("127.0.0.1", 8885), (("127.0.0.1", 8882), 1500)),
        ("rutas_R2_v5.txt", ("127.0.0.1", 8886), (("127.0.0.1", 7000), 1500)),
        ("rutas_R1_v5.txt", ("8.8.8.8", 53), (("127.0.0.1", 7000), 1500)),
        ("rutas_Rdefault_v5.txt", ("127.0.0.1", 8884), (("127.0.0.1", 8884), 1500)),
        ("rutas_Rdefault_v5.txt", ("8.8.8.8", 53), None)]:
    check(f"check_routes({table}, {destination})", check_routes(routes(table), destination), expected)


class FakeSocket:
    """Guarda lo que el router envía, en vez de enviarlo."""
    def __init__(self):
        self.sent = []

    def sendto(self, data, address):
        self.sent.append((parse_packet(data), address))


print("\n== Parte II, pasos 2 y 3: descarte y decremento del TTL en R2 del ejemplo 2")
for ttl, port, expected_ttl in [(0, 8883, None), (0, 8882, None), (1, 8883, 0), (10, 8883, 9), (1, 8882, None)]:
    fake_socket, output = FakeSocket(), io.StringIO()
    with contextlib.redirect_stdout(output):
        handle_packet(fake_socket, ("127.0.0.1", 8882), routes("rutas_R2_v2.txt"),
                      create_packet({"ip": "127.0.0.1", "port": port, "ttl": ttl, "message": b"hola"}))
    sent_ttl = fake_socket.sent[0][0]["ttl"] if fake_socket.sent else None
    print(f"llega a R2 con destino {port} y TTL {ttl}: imprime {output.getvalue().strip()!r}; "
          f"reenvía con TTL {sent_ttl}")
    assert sent_ttl == expected_ttl and len(fake_socket.sent) <= 1

# ==================================================
# ACTIVIDAD 6: Fragmentación
# ==================================================
print("== Check_routes con tablas que incluyen MTU")

# R1 -> R2: MTU 100.
check("R1 hacia R5", check_routes(routes("rutas_R1_v3_mtu.txt"), ("127.0.0.1", 8885)), (("127.0.0.1", 8882), 100))

# R2 -> R3 o R4: MTU 50 y 80.
r2_results = {check_routes(routes("rutas_R2_v3_mtu.txt"), ("127.0.0.1", 8885)) for _ in range(2)}
check("R2 hacia R5: alternativas y sus MTU", r2_results, {(("127.0.0.1", 8883), 50), (("127.0.0.1", 8884), 80)})

# R3 -> R2 o R5: MTU 50 y 55.
r3_results = {check_routes(routes("rutas_R3_v3_mtu.txt"), ("127.0.0.1", 8885)) for _ in range(2)}
check("R3 hacia R5: alternativas y sus MTU", r3_results, {(("127.0.0.1", 8882), 50), (("127.0.0.1", 8885), 55)})

# R4 -> R2 o R5: MTU 80 y 140.
r4_results = {check_routes(routes("rutas_R4_v3_mtu.txt"), ("127.0.0.1", 8885)) for _ in range(2)}
check("R4 hacia R5: alternativas y sus MTU", r4_results, {(("127.0.0.1", 8882), 80), (("127.0.0.1", 8885), 140)})

# R5 -> R4 o R3: MTU 140 y 55.
r5_results = {check_routes(routes("rutas_R5_v3_mtu.txt"), ("127.0.0.1", 8881)) for _ in range(2)}
check("R5 hacia R1: alternativas y sus MTU", r5_results, {(("127.0.0.1", 8884), 140), (("127.0.0.1", 8883), 55)})

print("\n== Fragmentación IP")
fragment_source = create_packet({"ip": "127.0.0.1", "port": 8885, "ttl": 10, "id": 42, "offset": 0, "flag": 0, "message": bytes(range(100))})
check("paquete que cabe en MTU 118", fragment_IP_packet(fragment_source, 118), [fragment_source])
check("cantidad de paquetes cuando no requiere fragmentación", len(fragment_IP_packet(fragment_source, 118)), 1)
fragments = fragment_IP_packet(fragment_source, 50)
check("cantidad de fragmentos para MTU 50", len(fragments), 4)
check("tamaño total de cada fragmento", [len(fragment) for fragment in fragments], [50, 50, 50, 22])
parsed_fragments = [parse_packet(fragment) for fragment in fragments]
check("offsets", [fragment["offset"] for fragment in parsed_fragments], [0, 32, 64, 96])
check("FLAG", [fragment["flag"] for fragment in parsed_fragments], [1, 1, 1, 0])
check("reensamblaje del mensaje", b"".join(fragment["message"] for fragment in parsed_fragments), bytes(range(100)))
reassembled = reassemble_IP_packet([fragments[2], fragments[0], fragments[3], fragments[1]])
check("reensamblaje del paquete completo con fragmentos desordenados", reassembled, fragment_source)
check("lista incompleta de fragmentos", reassemble_IP_packet(fragments[:-1]), None)
check("paquete sin fragmentar", reassemble_IP_packet([fragment_source]), fragment_source)

print("\n== Pruebas de FLAG al re-fragmentar ==")

packet_flag_1 = create_packet({
    "ip": "127.0.0.1",
    "port": 8885,
    "ttl": 10,
    "id": 350,
    "offset": 0,
    "flag": 1,
    "message": b"X" * 100
})

fragments_flag_1 = fragment_IP_packet(packet_flag_1, 50)
check("FLAG 1 se conserva en todos los subfragmentos", [parse_packet(f)["flag"] for f in fragments_flag_1], [1, 1, 1, 1])

packet_flag_0 = create_packet({
    "ip": "127.0.0.1",
    "port": 8885,
    "ttl": 10,
    "id": 351,
    "offset": 0,
    "flag": 0,
    "message": b"X" * 100
})

fragments_flag_0 = fragment_IP_packet(packet_flag_0, 50)
check("FLAG 0 solo en el último subfragmento", [parse_packet(f)["flag"] for f in fragments_flag_0], [1, 1, 1, 0])

print("\n== Recepción, almacenamiento y reensamblaje por ID")
received_packets.clear()
router_address = ("127.0.0.1", 8881)
packet_a = create_packet({"ip": router_address[0], "port": router_address[1], "ttl": 10, "id": 101, "message": b"ABCDEFGHIJKLMNO"})
packet_b = create_packet({"ip": router_address[0], "port": router_address[1], "ttl": 10, "id": 202, "message": b"1234567890abcde"})
fragments_a = fragment_IP_packet(packet_a, 23)
fragments_b = fragment_IP_packet(packet_b, 23)
received_order = [fragments_a[1], fragments_b[0], fragments_a[0], fragments_b[2], fragments_a[2], fragments_b[1]]
fake_socket, output = FakeSocket(), io.StringIO()
with contextlib.redirect_stdout(output):
    for fragment in received_order:
        handle_packet(fake_socket, router_address, routes("rutas_R1_v3.txt"), fragment)
check("IDs almacenados", set(received_packets), {101, 202})
check("fragmentos del ID 101", received_packets[101], [fragments_a[1], fragments_a[0], fragments_a[2]])
check("fragmentos del ID 202", received_packets[202], [fragments_b[0], fragments_b[2], fragments_b[1]])
check("mensajes reensamblados en orden de llegada completa", output.getvalue().splitlines(),
      ["ABCDEFGHIJKLMNO", "1234567890abcde"])
check("fragmentos locales no reenviados", fake_socket.sent, [])

print("\n== Pruebas de actividad 6 con configuración de 5 routers con MTU")
round_robin_state.clear()
small_packet = create_packet({"ip": "127.0.0.1", "port": 8885, "ttl": 10, "id": 347, "offset": 0, "flag": 0, "message": b"hola!"})
fake_socket = FakeSocket()
handle_packet(fake_socket, ("127.0.0.1", 8881), routes("rutas_R1_v3_mtu.txt"), small_packet)
check("paquete de 5 bytes no se fragmenta", len(fake_socket.sent), 1)
check("TTL del paquete reenviado", fake_socket.sent[0][0]["ttl"], 9)
check("ID del paquete reenviado", fake_socket.sent[0][0]["id"], 347)
check("destino del primer salto", fake_socket.sent[0][1], ("127.0.0.1", 8882))

round_robin_state.clear()
round_robin_hops = [check_routes(routes("rutas_R2_v3_mtu.txt"), ("127.0.0.1", 8885)) for _ in range(4)]
check("round-robin con MTU en R2", round_robin_hops, [(("127.0.0.1", 8883), 50), (("127.0.0.1", 8884), 80)] * 2)

large_packet = create_packet({"ip": "127.0.0.1", "port": 8885, "ttl": 10, "id": 348, "offset": 0, "flag": 0, "message": b"X" * 132})
fake_socket = FakeSocket()
handle_packet(fake_socket, ("127.0.0.1", 8881), routes("rutas_R1_v3_mtu.txt"), large_packet)
first_hop_fragments = [create_packet(fragment) for fragment, address in fake_socket.sent]
check("paquete de 150 bytes fragmentado en R1", len(first_hop_fragments), 2)
check("tamaño de fragmentos enviados por R1", [len(fragment) for fragment in first_hop_fragments], [100, 68])
check("destino de los fragmentos de R1", {address for _, address in fake_socket.sent}, {("127.0.0.1", 8882)})

fake_socket = FakeSocket()
for fragment in first_hop_fragments:
    handle_packet(fake_socket, ("127.0.0.1", 8882), routes("rutas_R2_v3_mtu.txt"), fragment)
check("refragmentación realizada por R2",
      all(len(create_packet(fragment)) <= (50 if address[1] == 8883 else 80)
          for fragment, address in fake_socket.sent),
      True)
check("R2 reenvía 4 fragmentos", len(fake_socket.sent), 4)

print("\nTodas las pruebas pasaron")
