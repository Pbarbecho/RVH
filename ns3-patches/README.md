# ns3-patches — parches del fork para un contenedor ya construido

Copia literal de los **10 ficheros** modificados en el fork
[Pbarbecho/VaN3TwinGEO](https://github.com/Pbarbecho/VaN3TwinGEO) (commit
`99ae881`). Las imágenes construidas a partir de ahora ya los incluyen (el
Dockerfile clona el fork); esta carpeta existe para los alumnos con un volumen
`ns3-workspace` anterior, donde el árbol ns-3 no es un repo git y no se puede
hacer `git pull`.

Qué contienen, por versión:

| Versión (commit) | Ficheros | Qué cambia |
|---|---|---|
| 9801a72 (sept. 2026) | traci-client.{h,cc}, vdpTraci.{h,cc}, caBasicService.cc, sumo-sensor.cc, MetricSupervisor.cc, ejemplo EVA | Rendimiento TraCI: instantáneas por suscripción, sensor y MetricSupervisor sin O(N²), flag `--pcap` (ver `RENDIMIENTO_SUMO_GEO.md` en el fork) |
| 99ae881 (nov. 2026) | + cpBasicService.cc, emergencyVehicleAlert.cc | **SUMO ya no queda huérfano** tras Ctrl+C o error (fork + PDEATHSIG + `KillSumo`), conexión TraCI con reintentos hasta 90 s, CPM válido con tranvías (dimensión saturada a 25,5 m), StationType ETSI según la vClass de SUMO (bus, tranvía, ciclista, moto…), `readLanePosition` sin excepciones en teletransportes, métricas finales de veh0..vehN-1 |

Aplicar (desde el host, contenedor en marcha): `./tools/apply-ns3-patches.sh`.
Se puede ejecutar las veces que haga falta: si el contenedor ya tiene esta
versión (marca `KillSumo` en `traci-client.h`) no hace nada; si tiene la
versión anterior, añade los ficheros nuevos a la copia de seguridad y
recompila. Deshacer: `./tools/revert-ns3-patches.sh`. Sin recompilar, las
suscripciones se desactivan con `--ns3::TraciClient::UseSubscriptions=false`.

Para actualizar esta carpeta tras un cambio en el fork: `cp` de los ficheros
listados en `git diff --name-only` respetando las rutas `src/...`, y cambiar
la marca `MARK` de `tools/apply-ns3-patches.sh` por una cadena que solo exista
en la versión nueva.
