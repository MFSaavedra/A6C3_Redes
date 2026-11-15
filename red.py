"""Levanta varios routers a la vez y muestra lo que imprime cada uno, precedido de su nombre.

Uso: python3 red.py tabla_1 tabla_2 ...      ej: python3 red.py rutas/rutas_R*_v3.txt

El nombre y el puerto de cada router salen del nombre de su tabla, rutas_<nombre>_<versión>.txt: RN
escucha en el puerto 8880 + N y Rdefault, el router default, en el 7000; todos en 127.0.0.1. Cuando
todos están escuchando se imprime una línea que empieza con "[red] listos". Ctrl+C o SIGTERM detiene
todos los routers, y si uno termina por su cuenta se detienen los demás.
"""
import os
import re
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

ROUTER_IP = "127.0.0.1"
ROUTER_SCRIPT = Path(__file__).resolve().parent / "router.py"
SPECIAL_PORTS = {"Rdefault": 7000}
output_lock = threading.Lock()


def router_name_and_port(routes_file):
    """Nombre y puerto del router que usa routes_file, según el nombre del archivo."""
    match = re.match(r"rutas_(R[^_]+)_", Path(routes_file).name)
    if match is None:
        sys.exit(f"{routes_file}: el nombre debe ser rutas_<router>_<versión>.txt")
    name = match.group(1)
    if name in SPECIAL_PORTS:
        return name, SPECIAL_PORTS[name]
    if re.fullmatch(r"R\d+", name):
        return name, 8880 + int(name[1:])
    sys.exit(f"{routes_file}: no se sabe en qué puerto escucha {name}")


def relay_output(name, process, started, first_lines):
    """Reimprime cada línea del router con su nombre. Guarda la primera línea en first_lines y
    activa started: si el router partió bien, es la línea que imprime cuando ya está escuchando."""
    for line in process.stdout:
        with output_lock:
            print(f"[{name}] {line}", end="", flush=True)
        first_lines.setdefault(name, line)
        started.set()
    started.set()  # también si el router terminó sin imprimir nada


def main():
    if len(sys.argv) < 2:
        sys.exit("Uso: python3 red.py tabla_1 tabla_2 ...")
    routers = [router_name_and_port(routes_file) + (routes_file,) for routes_file in sys.argv[1:]]
    ports = [port for _, port, _ in routers]
    if len(set(ports)) != len(ports):
        sys.exit("Hay dos tablas para routers con el mismo puerto")

    # SIGTERM termina con SystemExit, para que el finally detenga a los routers
    signal.signal(signal.SIGTERM, lambda signum, frame: sys.exit(0))
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    processes, relays, first_lines = [], [], {}
    try:
        for name, port, routes_file in routers:
            process = subprocess.Popen([sys.executable, str(ROUTER_SCRIPT), ROUTER_IP, str(port), routes_file],
                                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                       text=True, encoding="utf-8", errors="replace", env=env)
            started = threading.Event()
            relay = threading.Thread(target=relay_output, args=(name, process, started, first_lines), daemon=True)
            relay.start()
            processes.append(process)
            relays.append((relay, started))
        for _, started in relays:
            started.wait(timeout=10)
        failed = [name for name, _, _ in routers if " escuchando" not in first_lines.get(name, "")]
        if failed:
            with output_lock:
                print(f"[red] no partieron: {', '.join(failed)}; se detienen los demás", flush=True)
        else:
            listening = ", ".join(f"{name} en {ROUTER_IP}:{port}" for name, port, _ in routers)
            with output_lock:
                print(f"[red] listos: {listening}", flush=True)
            while all(process.poll() is None for process in processes):
                time.sleep(0.2)
            with output_lock:
                print("[red] un router terminó; se detienen los demás", flush=True)
    except KeyboardInterrupt:
        pass
    finally:
        for process in processes:
            if process.poll() is None:
                process.terminate()
        for process in processes:
            process.wait()
        for relay, _ in relays:
            relay.join(timeout=2)


if __name__ == "__main__":
    main()
