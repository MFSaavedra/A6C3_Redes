"""Resume una salida de red.py: los saltos y el camino de cada paquete, y su orden de llegada.

Uso: python3 pruebas/saltos.py salida.txt [--resumen]

Cada paquete se identifica por su mensaje, así que los mensajes de una prueba deben ser distintos.
Un salto es un reenvío ("redirigiendo paquete ..."). El camino se arma siguiendo los reenvíos de
cada paquete desde el router por donde entró a la red. Con --resumen no se muestra la tabla de
paquetes, solo los totales y el orden de llegada.
"""
import ast
import re
import sys
from collections import Counter

PACKET = r"\[(?P<ip>[\d.]+):(?P<port>\d+)(?:, TTL=(?P<ttl>\d+))?, (?P<message>'.*'|\".*\")\]"
FORWARD = re.compile(rf"redirigiendo paquete {PACKET} con destino final \S+ desde (?P<src>\S+) hacia (?P<dst>\S+)")
TTL_ZERO = re.compile(rf"Se recibió paquete {PACKET} con TTL 0")
NO_ROUTE = re.compile(rf"No hay rutas hacia \S+ para paquete {PACKET}")
STARTED = re.compile(r"Router (?P<address>\S+) escuchando")
LINE = re.compile(r"\[(?P<router>[^\]]+)\] (?P<text>.*)")
ERRORS = ("Se descarta un paquete inválido", "No se pudo ", "Error: ")  # avisos de error del router


class Packet:
    def __init__(self, order):
        self.order = order      # orden en que aparece por primera vez, es decir, de envío
        self.forwards = []      # (desde, hacia), en el orden del log
        self.outcome = None     # qué le pasó al final
        self.delivered_to = None


def build_path(packet, names):
    """Camino del paquete como lista de nombres de router, encadenando sus reenvíos."""
    if not packet.forwards:
        return [packet.delivered_to] if packet.delivered_to else []
    pending = list(packet.forwards)
    src, dst = pending.pop(0)
    path = [names.get(src, src), names.get(dst, dst)]
    current = dst
    while pending:
        # el siguiente reenvío sale del router donde quedó el paquete; si las líneas de dos routers
        # quedaron desordenadas en el log, se toma el primero que sale de ahí
        index = next((i for i, (s, _) in enumerate(pending) if s == current), 0)
        _, current = pending.pop(index)
        path.append(names.get(current, current))
    return path


def main():
    if len(sys.argv) not in (2, 3) or (len(sys.argv) == 3 and sys.argv[2] != "--resumen"):
        sys.exit("Uso: python3 pruebas/saltos.py salida.txt [--resumen]")
    names, packets, arrivals = {}, {}, []

    def packet_for(message):
        if message not in packets:
            packets[message] = Packet(len(packets))
        return packets[message]

    with open(sys.argv[1], encoding="utf-8", errors="replace") as log:
        for raw in log:
            line = LINE.fullmatch(raw.rstrip("\n"))
            if line is None or line["router"] == "red":
                continue
            router, text = line["router"], line["text"]
            if match := STARTED.match(text):
                names[match["address"]] = router
            elif match := FORWARD.fullmatch(text):
                packet_for(ast.literal_eval(match["message"])).forwards.append((match["src"], match["dst"]))
            elif match := TTL_ZERO.fullmatch(text):
                packet_for(ast.literal_eval(match["message"])).outcome = f"descartado por TTL en {router}"
            elif match := NO_ROUTE.fullmatch(text):
                packet_for(ast.literal_eval(match["message"])).outcome = f"sin ruta en {router}"
            elif text.startswith(ERRORS):
                continue
            else:  # un router imprime solo el mensaje cuando el paquete es para él
                packet = packet_for(text)
                packet.outcome, packet.delivered_to = f"llegó a {router}", router
                arrivals.append(packet.order)

    ordered = sorted(packets.items(), key=lambda item: item[1].order)
    if len(sys.argv) == 2:
        width = max((len(message) for message in packets), default=7)
        print(f"{'mensaje':<{width}}  saltos  {'resultado':<25}  camino")
        for message, packet in ordered:
            path = " ".join(build_path(packet, names))
            print(f"{message:<{width}}  {len(packet.forwards):>6}  {packet.outcome or 'sin resultado':<25}  {path}")

    delivered = [packet for _, packet in ordered if packet.delivered_to]
    print(f"\n{len(packets)} paquetes: {len(delivered)} llegaron a destino, "
          f"{sum(1 for _, p in ordered if p.outcome and 'TTL' in p.outcome)} descartados por TTL, "
          f"{sum(1 for _, p in ordered if p.outcome and 'sin ruta' in p.outcome)} sin ruta, "
          f"{sum(1 for _, p in ordered if p.outcome is None)} sin resultado")
    if delivered:
        hops = [len(packet.forwards) for packet in delivered]
        histogram = ", ".join(f"{h} saltos: {count}" for h, count in sorted(Counter(hops).items()))
        print(f"Saltos de los que llegaron: mínimo {min(hops)}, máximo {max(hops)}, "
              f"promedio {sum(hops) / len(hops):.2f} ({histogram})")
        # un paquete fue adelantado si llegó después de otro que se envió más tarde
        overtaken, latest = 0, -1
        for order in arrivals:
            overtaken += order < latest
            latest = max(latest, order)
        print(f"Orden de llegada (número de envío): {' '.join(str(order + 1) for order in arrivals)}")
        print(f"Paquetes adelantados por otro enviado después: {overtaken} de {len(arrivals)}")


if __name__ == "__main__":
    main()
