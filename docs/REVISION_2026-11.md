# Revisión de escenarios, scripts e integración ns-3 (noviembre 2026)

Revisión profunda de los tres repos del taller (van3twin-docker/RVH, SUMO_GEO,
VaN3TwinGEO) tras añadir el escenario multimodal de Cuenca. Todo lo marcado
como **corregido** está publicado en GitHub. Lo que no se pudo probar en la
nube (compilar ns-3, Docker) está marcado como **pendiente de validar en el
Mac**.

## 1. ns-3 (fork VaN3TwinGEO, commit `99ae881`)

| Gravedad | Hallazgo | Estado |
|---|---|---|
| Crítica | `traci-client.cc` lanzaba SUMO con `std::system("sumo … &")`: SIGINT ignorado, PID no guardado, nada lo mataba. Un Ctrl+C a ns-3 (o cualquier `NS_FATAL_ERROR`) dejaba un **SUMO huérfano** esperando clientes TraCI y la corrida siguiente saltaba a 3401, 3402… (lo que viste en clase). | **Corregido**: fork + exec, `PR_SET_PDEATHSIG`, `KillSumo()` en `SumoStop` y en todas las salidas por error. |
| Mayor | Un solo intento de conexión TraCI tras 1 s fijo (`SumoWaitForSocket`). Con redes grandes SUMO tarda más en abrir el puerto, ns-3 abortaba y SUMO seguía vivo. | **Corregido**: reintentos cada 250 ms hasta 90 s, abortando limpio si SUMO muere antes. |
| Mayor | El CPM codifica las dimensiones del objeto percibido como `ObjectDimensionValue (1..256)`, no `(1..1023)` como el CAM. Un tranvía (32,5 m → 325) hacía fallar la codificación UPER y el CPM se descartaba **en silencio**. | **Corregido**: saturado a 255 (`outOfRange`). |
| Mayor | `emergencyVehicleAlert` solo distinguía `passenger` y `emergency`; buses, tranvías, bicis y motos salían como `StationType_unknown` en CAM/DENM y en el visor, y además ejecutaban la maniobra de ceder el paso (un tranvía "cambiaba de carril", una bici "aceleraba al 150 %"). | **Corregido**: StationType ETSI por vClass; la maniobra solo la hacen vehículos de carretera a motor. |
| Menor | `readLanePosition` lanzaba una excepción TraCI con `roadId` vacío (teletransporte) que escapaba del bucle de eventos y abortaba la simulación. | **Corregido**: devuelve `offTheRoad`. |
| Menor | El listado final de métricas por vehículo recorría 1..N: omitía veh0 y añadía una fila fantasma. | **Corregido**: 0..N-1. |
| Menor | Si una suscripción falla, todo el run vuelve al modo O(N²) con solo un `NS_LOG_WARN`. | Documentado; no cambiado. |
| Menor | El primer snapshot de cada vehículo hace 4 round-trips extra y deja `accel`/`laneIndex` a 0 hasta el paso siguiente. | Documentado; no cambiado (una CAM). |

Verificado OK en el código: conteo de vehículos (`//vehicle` = 240),
StationID = `stol(id.substr(3))` = 0..239, línea de órdenes de SUMO
(`--num-clients` desde `--num-traci-clients`, `setOrder(1)`), `RefreshSnapshots`
una vez por paso, variables suscritas cubren todo lo que lee el VDP,
dimensiones CAM dentro de rango (tranvía 325/26 ≤ 1023/62), tasa de
penetración (no equipados quedan fuera de los nodos y de los denominadores de
PRR), compatibilidad del cliente 2 (visor, pasos de 0,5 s múltiplos de 0,01 s).

**Pendiente de validar en el Mac**: aquí no se puede compilar ns-3 (las
cabeceras de módulo se generan al configurar). Compilar con
`./tools/apply-ns3-patches.sh` (10-30 min) y comprobar: (1) Ctrl+C a
`./ns3 run` ya no deja `sumo` en `ps aux`; (2) con `--penetrationRate=0.7` las
CAM de buses/tranvías llevan `stationType` 6/11; (3) `Average PRR of vehicle 0`
aparece en la salida final.

## 2. Escenarios SUMO (van3twin-docker/results)

| Gravedad | Hallazgo | Estado |
|---|---|---|
| Mayor | `cuenca.sumocfg` y `cuenca_mixed.sumocfg` escribían `co2.xml` (21 MB), `fcd.xml` (11 MB) y `tripinfo.xml` en cada corrida de ns-3, y estaban subidos al repo. | **Corregido**: salidas movidas a `cuenca_salidas.sumocfg` / `cuenca_mixed_salidas.sumocfg` (para sumo-gui), ficheros retirados del repo e ignorados por git. |
| Mayor | `enrich_heights.py` no reconocía los ids `wayid#n` que polyconvert emite cuando un way tiene varios tipos, ni los edificios de relaciones multipolígono: 45 edificios del multimodal tenían la altura por defecto (iglesia 14 m → 10 m, teatro 18 m → 10 m). | **Corregido** en ambos repos y regenerado `cuenca_mm.poly.xml`. |
| Mayor | `results/cuenca/cuenca_high.rou.xml` (4805 vehículos) colapsa la red: 502 teletransportes y 1108 vehículos nunca entran. Ningún sumocfg lo usa, pero ns-3 crearía 4805 nodos. | No cambiado; no usarlo con ns-3. |
| Menor | `cuenca_mm.sumocfg` terminaba en 1200 s con 6 vehículos aún en ruta (el tranvía de las 750 s a mitad de paradas). | **Corregido**: fin 1500 s (los 240 llegan, 20 paradas cumplidas). |
| Menor | `build_multimodal.sh` resolvía `OSM` relativo después del `cd`. | **Corregido**. |
| Menor | El comando de ns-3 del README para `results/cuenca` no llevaba `--sim-time` (el ejemplo simula 50 s por defecto frente a 3600 s de demanda). | **Corregido**. |
| Menor | `cuenca_low.xml` era una copia huérfana e idéntica de `cuenca.rou.xml`. | **Eliminado**. |
| Menor | 4 peatones atascados en un mismo cruce del multimodal. | Cosmético; no cambiado. |

Verificado OK con SUMO 1.12: `cuenca_mm.sumocfg` 240 insertados, 0
teletransportes, 0 colisiones, tranvías con todas sus paradas, las 3 rutas de
ambulancia válidas para `emergency`, todas las rutas conectadas;
`cuenca_mm_peatones.sumocfg` 450 personas; `build_multimodal.sh` reproduce los
ficheros byte a byte; todas las opciones de netconvert/polyconvert/randomTrips
existen en 1.12; el paquete `sumo-tools` de Ubuntu 22.04 incluye
`randomTrips.py` y los typemaps en `/usr/share/sumo`.

## 3. Generadores del repo SUMO_GEO

| Gravedad | Hallazgo | Estado |
|---|---|---|
| Crítica | `gen_traffic.py --tram` generaba flujos de tipo `tram` sin definirlo en `transit.add.xml`: SUMO abortaba al cargar. | **Corregido**: vType `tram` añadido. |
| Crítica | `sumo/cuenca.net.xml` se construyó con netconvert 1.27 y usa vClasses que SUMO 1.12 (el del contenedor) no conoce: no carga en van3twin. | Documentado en el README; los escenarios para ns-3 deben generarse con el netconvert del contenedor (como `cuenca_multimodal`). |
| Mayor | `gen_traffic.py` no era reproducible: `hash(str)` cambia en cada proceso aunque se fije `--seed`. | **Corregido**. |
| Mayor | `cuenca_{low,mid,high}.rou.xml` son trips sin enrutar: ~23 % no tiene ruta y SUMO los descarta, así que la demanda real es menor que la nominal. | Documentado; regenerar con `gen_traffic.py` (modo duarouter) requiere SUMO 1.27 en el host. |
| Menor | El sumocfg de `gen_traffic.py` solo valía si `--outdir` era la carpeta de la red. | **Corregido**: rutas relativas. |
| Menor | `generate_scenario.sh` llamaba a `python` en vez de `python3`. | **Corregido**. |

## 4. Docker, scripts de parches y visor

| Gravedad | Hallazgo | Estado |
|---|---|---|
| Mayor | `apply-ns3-patches.sh` hacía la copia de seguridad de lo que hubiera en el contenedor sin comprobar si ya estaba parcheado, y `tar` abortaba si faltaba un fichero nuevo. | **Corregido**: marca de versión (`KillSumo`), ficheros nuevos añadidos al tar existente, `chown vanet` tras `docker cp`, comprobación de contenedor en `revert`. |
| Mayor | El visor en modo remoto se quedaba bloqueado para siempre en "esperando a SUMO" ante un SUMO huérfano que acepta la conexión pero no responde. | **Corregido** en el commit anterior de SUMO_GEO (tope de 10 s por puerto, log por puerto). |
| Menor | Sin ningún navegador abierto, el visor no avanza y ns-3 espera (es intencionado, `APP_HOLD_WITHOUT_VIEWERS`), pero no estaba en el README. | **Documentado**. |

## Qué tienen que hacer los alumnos

```bash
cd van3twin-docker
git pull
docker compose --profile visor pull backend frontend
docker compose --profile visor up -d
./tools/apply-ns3-patches.sh        # recompila ns-3 con las correcciones (10-30 min)
```
