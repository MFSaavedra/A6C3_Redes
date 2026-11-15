"""Simula, sin sockets, el camino de paquetes enviados de a uno de R1 a R5, con check_routes.

Uso: python3 pruebas/simulacion.py [N]

Para las redes de 5 (v3) y de 7 routers (v4), sigue N paquetes (1000 por omisión), cada uno desde
que entra a R1 hasta que llega a R5, consultando check_routes con la tabla de cada router. Como cada
paquete llega antes de que salga el siguiente, el resultado es el mismo que en la red real (ver
pruebas/round_robin.sh) y muestra cómo se comportan los saltos a largo plazo.
"""
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import router  # noqa: E402


def simulate(version, n):
    """Saltos de cada uno de n paquetes de R1 (8881) a R5 (8885) en la red version."""
    router.round_robin_state.clear()
    hops = []
    for _ in range(n):
        port, count = 8881, 0
        while port != 8885:
            routes_file = ROOT / "rutas" / f"rutas_R{port - 8880}_{version}.txt"
            port = router.check_routes(str(routes_file), ("127.0.0.1", 8885))[1]
            count += 1
        hops.append(count)
    return hops


def period(hops):
    """Período con que se repite la secuencia de saltos, descartando los primeros 100 paquetes."""
    tail = hops[100:]
    return next((p for p in range(1, len(tail) // 2) if tail[:-p] == tail[p:]), None)


n = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
for version, description in (("v3", "5 routers"), ("v4", "7 routers")):
    hops = simulate(version, n)
    histogram = ", ".join(f"{h}: {count}" for h, count in sorted(Counter(hops).items()))
    print(f"Red de {description} ({version}), {n} paquetes de R1 a R5:")
    print(f"  primeros 12: {hops[:12]}")
    print(f"  mínimo {min(hops)}, máximo {max(hops)}, promedio {sum(hops) / n:.3f}")
    print(f"  saltos: cantidad de paquetes -> {histogram}")
    p = period(hops)
    if p:
        print(f"  la secuencia se repite cada {p} paquetes, con promedio {sum(hops[100:100 + p]) / p:.3f}")
