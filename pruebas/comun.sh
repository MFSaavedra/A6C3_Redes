# Funciones comunes de los escenarios de prueba. Cada script de pruebas/ las carga con
#   . "$(dirname "$0")/comun.sh"
# y desde ahí trabaja en la raíz del repositorio, con las salidas en pruebas/salida/.
cd "$(dirname "$0")/.." || exit 1
mkdir -p pruebas/salida

# iniciar_red LOG TABLA...: levanta con red.py los routers de las tablas, con su salida en LOG, y
# espera a que todos estén escuchando
iniciar_red() {
    log=$1
    shift
    python3 red.py "$@" > "$log" 2>&1 &
    red_pid=$!
    intentos=0
    until grep -q '^\[red\] listos' "$log"; do
        intentos=$((intentos + 1))
        if [ "$intentos" -gt 100 ] || ! kill -0 "$red_pid" 2>/dev/null; then
            echo "La red no partió:" >&2
            cat "$log" >&2
            detener_red
            exit 1
        fi
        sleep 0.05
    done
}

# esperar_red: espera a que los routers dejen de imprimir, como máximo 10 s
esperar_red() {
    anterior=-1
    for _ in $(seq 50); do
        sleep 0.2
        actual=$(wc -c < "$log")
        [ "$actual" -eq "$anterior" ] && return
        anterior=$actual
    done
}

# detener_red: detiene red.py, que a su vez detiene los routers
detener_red() {
    kill "$red_pid" 2>/dev/null
    wait "$red_pid" 2>/dev/null
}

# enviar ARGUMENTOS: envía un paquete con enviar.py y espera 0.1 s, así que cada paquete llega a
# destino antes de que salga el siguiente
enviar() {
    python3 enviar.py "$@" || exit 1
    sleep 0.1
}
