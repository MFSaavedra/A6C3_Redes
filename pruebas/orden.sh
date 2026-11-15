#!/bin/sh
# Prueba 2 con TTL: envía un archivo con prueba_router.py de R1 a R5, una línea por paquete y sin
# pausas, y muestra cuántos llegaron, con cuántos saltos y en qué orden.
#   sh pruebas/orden.sh [TTL] [archivo] [red]
# Por omisión el TTL es 10, como en el ejemplo del enunciado; el archivo es
# pruebas/archivo_grande.txt, de 100 líneas numeradas, y la red es v3, la de 5 routers (v4 es la de
# 7). La salida queda en pruebas/salida/orden_<red>_ttl<TTL>.txt.
. "$(dirname "$0")/comun.sh"
ttl=${1:-10}
archivo=${2:-pruebas/archivo_grande.txt}
red=${3:-v3}

iniciar_red "pruebas/salida/orden_${red}_ttl$ttl.txt" rutas/rutas_R*_"$red".txt
python3 prueba_router.py "127.0.0.1;8885;$ttl" 127.0.0.1 8881 < "$archivo" || exit 1
esperar_red
detener_red
python3 pruebas/saltos.py "$log" --resumen
echo "Primeras 20 líneas que imprimió R5:"
grep '^\[R5\] ' "$log" | grep -v 'escuchando\|redirigiendo\|con TTL 0$' | head -n 20 | sed 's/^\[R5\] /  /'
