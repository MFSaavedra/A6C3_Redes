#!/bin/sh
# Paso 3 de la parte II: paquetes de R1 a R3 en la red del ejemplo 2 (R1 - R2 - R3) con TTL 1, el
# del enunciado, 2 y 3.
#   sh pruebas/ttl.sh
. "$(dirname "$0")/comun.sh"

iniciar_red pruebas/salida/ttl.txt rutas/rutas_R1_v2.txt rutas/rutas_R2_v2.txt rutas/rutas_R3_v2.txt
enviar 127.0.0.1 8883 "hola" 127.0.0.1 8881 1
enviar 127.0.0.1 8883 "hola con TTL 2" 127.0.0.1 8881 2
enviar 127.0.0.1 8883 "hola con TTL 3" 127.0.0.1 8881 3
esperar_red
detener_red
cat pruebas/salida/ttl.txt
