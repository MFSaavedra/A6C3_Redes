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
from router import check_routes, create_packet, fragment_IP_packet, handle_packet, parse_packet  # noqa: E402


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

print("\nTodas las pruebas pasaron")
