#!/bin/sh
# Paso 8 de la parte I y pruebas 2 y 3 sin TTL: round-robin en las redes de 5 y de 7 routers.
#   sh pruebas/round_robin.sh [N]
# Envía N paquetes de R1 a R5 (8 por omisión) en la red de 5 routers y luego en la de 7, y por
# último, en la de 7 routers, N de R1 a R5 intercalados con N de R5 a R1 (test 2 del paso 8). Los
# paquetes salen de a uno: cada uno llega antes de que salga el siguiente. Al final muestra los
# saltos y el camino de cada paquete.
. "$(dirname "$0")/comun.sh"
n=${1:-8}

iniciar_red pruebas/salida/round_robin_v3.txt rutas/rutas_R*_v3.txt
for i in $(seq "$n"); do
    enviar 127.0.0.1 8885 "R1 a R5 #$i" 127.0.0.1 8881
done
esperar_red
detener_red

iniciar_red pruebas/salida/round_robin_v4.txt rutas/rutas_R*_v4.txt
for i in $(seq "$n"); do
    enviar 127.0.0.1 8885 "R1 a R5 #$i" 127.0.0.1 8881
done
esperar_red
detener_red

iniciar_red pruebas/salida/round_robin_v4_intercalado.txt rutas/rutas_R*_v4.txt
for i in $(seq "$n"); do
    enviar 127.0.0.1 8885 "R1 a R5 #$i" 127.0.0.1 8881
    enviar 127.0.0.1 8881 "R5 a R1 #$i" 127.0.0.1 8885
done
esperar_red
detener_red

for prueba in v3 v4 v4_intercalado; do
    echo "--- round_robin_$prueba"
    python3 pruebas/saltos.py "pruebas/salida/round_robin_$prueba.txt"
done
echo "--- R2 en la red de 7 routers con paquetes intercalados: siguiente salto según el destino"
for destino in 8885 8881; do
    echo "hacia 127.0.0.1:$destino: $(grep "^\[R2\] redirigiendo.*destino final 127.0.0.1:$destino " \
        pruebas/salida/round_robin_v4_intercalado.txt | sed 's/.*hacia 127.0.0.1://' | tr '\n' ' ')"
done
