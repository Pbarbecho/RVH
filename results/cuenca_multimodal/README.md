# Cuenca multimodal: peatones, tranvía y ciclovías

Centro histórico de Cuenca (~1,3 × 1 km, mismo recorte OSM que `results/cuenca`)
con toda la red no motorizada y el **Tranvía de los Cuatro Ríos**. Generado con
**SUMO 1.12**, la versión del contenedor ns-3, para que cargue sin avisos.

| Red | Cantidad |
|---|---|
| Aristas de calzada | 668 |
| Aristas peatonales (aceras propias, calles peatonales, escalinatas, sendas) | 598 |
| Carriles de acera (incluye los de calles con tráfico) | 1 090 |
| Pasos de cebra | 759 |
| Carriles bici (`cycleway=lane/track` de OSM) | 11 tramos |
| Vía de tranvía | 33 aristas, 2 líneas, 6 paradas |
| Edificios con altura · zonas verdes/agua/parkings · árboles | 2 894 · 187 · 505 |

| Demanda (salidas de 0 a 900 s) | Vehículos |
|---|---|
| Turismos, motos y buses (75 / 18 / 7 %) | 192 |
| Bicicletas | 38 |
| Tranvías (cada 300 s por sentido, 20 s por parada) | 7 |
| Ambulancias (`vClass="emergency"`, activan la aplicación EVA) | 3 |
| **Total = nodos ns-3** | **240** |
| Peatones (solo SUMO / sumo-gui, ver abajo) | 450 |

Comprobado en SUMO 1.12: los 240 vehículos se insertan, sin teletransportes ni
colisiones, y los tranvías cumplen todas sus paradas.

## Ficheros

| Fichero | Para qué |
|---|---|
| `cuenca_mm.net.xml` | Red multimodal (calles, aceras, cruces, ciclovías, tranvía) |
| `cuenca_mm.poly.xml` | Edificios 3D, zonas verdes, agua, aparcamientos, árboles |
| `cuenca_mm.ptstops.xml` · `cuenca_mm.ptlines.xml` | Paradas y líneas del tranvía (de OSM) |
| `cuenca_mm.rou.xml` | Vehículos, todos `veh<N>` |
| `cuenca_mm.peatones.rou.xml` | Peatones (`<person>`) |
| `cuenca_mm.sumocfg` | **ns-3**: vehículos, sin peatones |
| `cuenca_mm_peatones.sumocfg` | **SUMO / sumo-gui**: vehículos y peatones |
| `build_multimodal.sh` · `make_routes.py` · `enrich_heights.py` · `cuenca_mm.vtypes.add.xml` | Regenerar todo |

## Simular en ns-3 con el visor

1. En el Mac/PC, fichero `.env` de la carpeta `van3twin-docker`:

   ```bash
   SUMO_GEO_NET=/replay/cuenca_multimodal/cuenca_mm.net.xml
   SUMO_GEO_POLY=/replay/cuenca_multimodal/cuenca_mm.poly.xml
   ```

   y `docker compose --profile visor up -d`. Comprobación:
   `curl localhost:8000/api/meta` muestra `"rail":33`, `"bikelanes":11` y
   `"crossings":759`.

2. Lanzar el ejemplo con este escenario:

   ```bash
   docker compose exec van3twin ./ns3 run "v2v-emergencyVehicleAlert-80211p \
     --sumo-folder=/home/vanet/results/cuenca_multimodal/ \
     --mob-trace=cuenca_mm.rou.xml \
     --sumo-config=/home/vanet/results/cuenca_multimodal/cuenca_mm.sumocfg \
     --sim-time=300 --sumo-gui=false --met-sup=true --num-traci-clients=2"
   ```

   Abre `http://localhost:8081`. El visor dibuja el tranvía como vía con
   carriles, los carriles bici en azul, las aceras y cebras, y cada vehículo
   con su modelo: tranvía articulado, bici con ciclista, moto con motorista.

`--sim-time=300` sirve para una primera prueba; para ver la demanda completa
usa `--sim-time=1200`. Con 240 nodos, `--pcap=false` reduce mucho el tiempo
si no necesitas los pcap.

## Por qué los peatones van aparte

* El cliente TraCI de VaN3Twin crea **un nodo ns-3 por cada peatón** de SUMO,
  pero el ejemplo EVA reserva nodos contando solo los `<vehicle>` del
  `.rou.xml`. Con peatones aborta con `Node Pool empty!`.
* Por eso `cuenca_mm.sumocfg` no carga `cuenca_mm.peatones.rou.xml`. La red
  peatonal sí está en ambos: aceras, cruces y calles peatonales se ven igual.
* Para ver los peatones moviéndose:
  `sumo-gui -c cuenca_mm_peatones.sumocfg`. El visor web no dibuja personas.

Otras reglas del ejemplo EVA que el generador respeta: cada vehículo es un
`<vehicle>` explícito, sin `<flow>`, y su id es `veh<N>`, porque la
aplicación calcula el StationID con `std::stol(id.substr(3))`.

## Regenerar o cambiar la demanda

Dentro del contenedor, que ya tiene SUMO 1.12 en `/usr/share/sumo`:

```bash
docker compose exec van3twin bash -c 'cd ~/results/cuenca_multimodal && ./build_multimodal.sh'
# más tráfico, tranvía cada 4 min y 20 minutos de salidas:
docker compose exec van3twin bash -c 'cd ~/results/cuenca_multimodal && \
  CAR_PERIOD=2 TRAM_HEADWAY=240 END=1200 ./build_multimodal.sh'
```

Variables: `END`, `CAR_PERIOD`, `BIKE_PERIOD`, `PED_PERIOD`, `TRAM_HEADWAY`,
`SEED`. Cada vehículo más es un nodo ns-3 más, y el coste de ns-3 crece
aproximadamente con el cuadrado del número de nodos.

## Limitaciones

* El recorte deja el tranvía partido: la línea de ida tiene 2,9 km y 5
  paradas; la de vuelta, 1,7 km y 1 parada (Santo Domingo). Ambas entran y
  salen por el borde del mapa.
* OSM no tiene ciclovías segregadas en este recorte: los carriles bici salen
  de las etiquetas `cycleway=lane/track` de 11 tramos. Las bicis circulan
  también por las calles normales.
* `--osm.crossings` no existe en SUMO 1.12: las cebras salen de
  `--crossings.guess`.
