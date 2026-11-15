# CC4303 — Actividad 5: forwarding básico

Actividad 5 del curso **Redes (CC4303)**, DCC — Universidad de Chile.
Simula un mini-Internet con sockets UDP: cada router es un proceso que escucha en un par
(IP, puerto) y reenvía paquetes IP simulados según su tabla de rutas. Las rutas alternativas hacia
una misma área de la red se usan por turnos (round-robin) y los paquetes que llegan con TTL 0 se
descartan. Solo se usa la librería estándar de Python.

Integrantes: María Moya G., M. Fernando Saavedra.

## Ejecución

```bash
python3 router.py 127.0.0.1 8881 rutas/rutas_R1_v3.txt          # un router
python3 red.py rutas/rutas_R*_v3.txt                            # todos los routers de una red
python3 enviar.py 127.0.0.1 8885 "hola R5" 127.0.0.1 8881 [TTL]
python3 prueba_router.py "127.0.0.1;8885;10" 127.0.0.1 8881 < archivo.txt
```

`router.py` recibe su IP, su puerto y su tabla de rutas. `red.py` levanta varios routers a la vez y
muestra lo que imprime cada uno precedido de su nombre; deduce el router y su puerto del nombre de
cada tabla (`rutas_RN_*` escucha en el puerto 8880 + N y `rutas_Rdefault_*` en el 7000), y Ctrl+C
los detiene. `enviar.py` envía un mensaje: primero la dirección del router final, luego el mensaje
(entre comillas si tiene espacios), la dirección del router por donde entra a la red y,
opcionalmente, el TTL, que por omisión es 64. `prueba_router.py` envía cada línea de la entrada
estándar, o del archivo que se le pase como cuarto argumento, en un paquete distinto; los headers
`IP;puerto;TTL` van entre comillas porque la shell interpreta `;`.

## Tablas de rutas

Las tablas de `rutas/` se llaman `rutas_RN_vK.txt`:

- **v1**: ejemplo 1 de la guía, R1 — R2.
- **v2**: ejemplo 2 de la guía, R1 — R2 — R3. `rutas_R2_v2_mala.txt` es la tabla mal configurada
  de las pruebas.
- **v3**: red de 5 routers del enunciado.
- **v4**: red de 7 routers: la de 5 más R0 (8880), conectado a R1 y R2, y R6 (8886), conectado a R2
  y R3.
- **v5**: red de 5 routers con el router default `Rdefault` (7000), con la ruta default en la última
  línea de cada tabla.

## Pruebas

```bash
python3 pruebas/test_funciones.py          # parse_packet, create_packet, check_routes y TTL, sin sockets
sh pruebas/ejemplos.sh                     # redes de los ejemplos 1 y 2
sh pruebas/round_robin.sh [N]              # round-robin en las redes de 5 y 7 routers
sh pruebas/default.sh                      # router default
sh pruebas/mal_configurada.sh [TTL]        # tabla de R2 mal configurada
sh pruebas/ttl.sh                          # descarte por TTL
sh pruebas/orden.sh [TTL] [archivo] [red]  # orden de llegada al enviar un archivo
python3 pruebas/saltos.py salida.txt       # saltos y camino de cada paquete de una salida de red.py
python3 pruebas/simulacion.py [N]          # saltos de N paquetes enviados de a uno, sin sockets
```

Las salidas quedan en `pruebas/salida/`.

## Archivos

- **`router.py`**: el router y las funciones `parse_packet`, `create_packet` y `check_routes`.
- **`enviar.py`** y **`prueba_router.py`**: envían un mensaje y un archivo, respectivamente.
- **`red.py`**: levanta varios routers a la vez.
- **`rutas/`**: tablas de rutas.
- **`pruebas/`**: scripts de prueba y el archivo de 100 líneas que usa `orden.sh`.
- **`Informe/`**: informe LaTeX (`main.tex`), que se compila con `latexmk -pdf main.tex`. Las figuras
  de las redes están en `Informe/img/` como fuentes `.dot` y se regeneran con
  `sh Informe/img/diagramas.sh`.
