#!/bin/sh
# Paso 7 de la parte I: redes de los ejemplos 1 (R1 - R2) y 2 (R1 - R2 - R3). Envía paquetes a R1
# con destino R1, R2 y R3, y uno con destino fuera de la red (puerto 8884); en el ejemplo 2, uno
# más de R3 a R1.
#   sh pruebas/ejemplos.sh
. "$(dirname "$0")/comun.sh"

iniciar_red pruebas/salida/ejemplo1.txt rutas/rutas_R1_v1.txt rutas/rutas_R2_v1.txt
enviar 127.0.0.1 8881 "hola R1" 127.0.0.1 8881
enviar 127.0.0.1 8882 "hola R2" 127.0.0.1 8881
enviar 127.0.0.1 8883 "hola R3" 127.0.0.1 8881
esperar_red
detener_red

iniciar_red pruebas/salida/ejemplo2.txt rutas/rutas_R1_v2.txt rutas/rutas_R2_v2.txt rutas/rutas_R3_v2.txt
enviar 127.0.0.1 8881 "hola R1" 127.0.0.1 8881
enviar 127.0.0.1 8882 "hola R2" 127.0.0.1 8881
enviar 127.0.0.1 8883 "hola R3" 127.0.0.1 8881
enviar 127.0.0.1 8884 "hola" 127.0.0.1 8881
enviar 127.0.0.1 8881 "hola R1, soy R3" 127.0.0.1 8883
esperar_red
detener_red

for prueba in ejemplo1 ejemplo2; do
    echo "--- $prueba"
    cat "pruebas/salida/$prueba.txt"
done
