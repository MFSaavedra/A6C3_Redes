#!/bin/sh
# Paso 9 de la parte I: red de 5 routers con el router default (127.0.0.1:7000). Envía un paquete
# dentro de la red y dos hacia afuera: uno a un puerto sin router y otro a una IP de otra red.
#   sh pruebas/default.sh
. "$(dirname "$0")/comun.sh"

iniciar_red pruebas/salida/default.txt rutas/rutas_R*_v5.txt
enviar 127.0.0.1 8885 "hola R5" 127.0.0.1 8881
enviar 127.0.0.1 8886 "hola R6" 127.0.0.1 8881
enviar 10.0.0.1 8881 "hola 10.0.0.1" 127.0.0.1 8883
esperar_red
detener_red
cat pruebas/salida/default.txt
