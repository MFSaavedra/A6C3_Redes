#!/bin/sh
# Prueba 1 sin TTL y prueba 1 con TTL: red del ejemplo 2 con la tabla de R2 mal configurada
# (rutas_R2_v2_mala.txt). Envía a R1 un paquete con destino R3.
#   sh pruebas/mal_configurada.sh [TTL]
# La red se detiene 2 s después del envío, porque un paquete que da vueltas no deja de imprimirse.
# La salida queda en pruebas/salida/mal_configurada[_ttlN].txt, y se muestran sus primeras líneas
# y la cantidad de reenvíos.
. "$(dirname "$0")/comun.sh"
ttl=$1

iniciar_red "pruebas/salida/mal_configurada${ttl:+_ttl$ttl}.txt" \
    rutas/rutas_R1_v2.txt rutas/rutas_R2_v2_mala.txt rutas/rutas_R3_v2.txt
python3 enviar.py 127.0.0.1 8883 "hola R3" 127.0.0.1 8881 $ttl || exit 1
sleep 2
detener_red
head -n 25 "$log"
echo "..."
echo "$(grep -c 'redirigiendo paquete' "$log") reenvíos en 2 s; R3 recibió el mensaje $(grep -c '^\[R3\] hola R3$' "$log") veces"
