# Manual de actualización — VaN3Twin + visor SUMO-GEO (septiembre 2026)

Guía paso a paso para actualizar una instalación ya existente de
`van3twin-docker` a la versión de septiembre de 2026. Los cambios optimizan el
visor 3D y el acoplamiento con ns-3 para escalar a cientos de vehículos (detalle
en `docs/RENDIMIENTO_2026-09.md` del repo SUMO_GEO).

**Tiempo total:** 20-40 minutos, casi todo de espera (compilación).
**No se pierde nada:** ni tu código en el volumen `ns3-workspace`, ni los
resultados de `results/`.

---

## 0. Antes de empezar

| Necesitas | Cómo comprobarlo |
|---|---|
| Docker Desktop abierto | icono de la ballena en la barra, `docker ps` responde |
| Internet | las imágenes descargan código de GitHub al reconstruirse |
| ~5 GB libres en disco | `docker system df` muestra el espacio usado por Docker |
| Una terminal en la carpeta `van3twin-docker` | Mac: Terminal · Windows: terminal de **Ubuntu (WSL2)** o PowerShell |

Antes de tocar nada:

1. Cierra cualquier simulación en curso (`./ns3 run …`) con Ctrl+C y las
   pestañas del visor.
2. Si editaste `docker-compose.yml` (por ejemplo la línea `platform:`), guarda
   ese cambio: `git stash`. Lo recuperas al final con `git stash pop`.

---

## 1. Actualizar el repositorio (1 min)

```bash
cd van3twin-docker
git pull
```

Si `git pull` se queja de cambios locales: `git stash`, `git pull`,
`git stash pop`.

Comprueba la línea `platform:` del `docker-compose.yml`: debe estar activa
`linux/amd64` en PC Windows/Linux y `linux/arm64` en Mac Apple Silicon (M1-M4).

---

## 2. Reconstruir el visor (3-5 min)

Las imágenes `backend` y `frontend` clonan el repo SUMO_GEO al construirse: hay
que reconstruirlas **sin caché** para traer el código nuevo, y **las dos a la
vez** (hablan un protocolo nuevo y no funcionan mezcladas con versiones
antiguas).

```bash
docker compose --profile visor build --no-cache backend frontend
docker compose --profile visor up -d
```

Este paso **no** reconstruye la imagen `van3twin` (la de ns-3, que tarda
horas): solo el visor.

Comprobación:

```bash
curl localhost:8000/api/health
```

Debe devolver `"proto":2`. Si devuelve otra cosa, repite el paso con
`--no-cache`.

---

## 3. Parches de ns-3 dentro del contenedor (10-30 min)

El árbol ns-3 de tu volumen **no es un repositorio git** (el instalador de
VaN3Twin borra `.git`), así que los parches se copian con un script desde el
host. Con el contenedor arrancado :

```bash
docker compose up -d
```

### Desde otra terminal y desde el directorio van3twin ejecute:

```bash
./tools/apply-ns3-patches.sh
```

El script guarda los ficheros originales dentro del contenedor, copia los 8
ficheros parcheados de `ns3-patches/` y lanza `./ns3 build` (solo recompila
los módulos `traci` y `automotive`). Termina con
`'build' finished successfully`.


### Notas

- Durante la compilación verás avisos `warning` y `#pragma message ... deprecated`
  de Boost y de los tests de `cv2x`: son normales y no son errores.
- Un error real es una línea que empieza por `error:` seguida de
  `ninja: build stopped`. Copia las 30 líneas anteriores y envíalas al profesor.
- Si aún no habías arrancado nunca el contenedor (volumen vacío), este paso no
  hace falta: la imagen nueva ya trae los parches.
- Para deshacer: `./tools/revert-ns3-patches.sh` (restaura los originales y
  recompila).

Comprobación:

```bash
docker compose exec van3twin bash -c 'grep -c VehicleSnapshot ~/VaN3Twin/ns-3-dev/src/traci/model/traci-client.h'
```

Debe imprimir un número mayor que 0.

---

## 4. Probar que todo funciona

1. Abre `http://localhost:8081` y recarga con **Ctrl+Shift+R** (Cmd+Shift+R en
   Mac) para descartar el `app.js` antiguo. En el panel izquierdo debe aparecer
   la casilla **Modo ligero** y en la barra superior el botón 🖱.
2. Lanza el ejemplo EVA dentro del contenedor:

   ```bash
   docker compose exec van3twin bash
   cd ~/VaN3Twin/ns-3-dev
   ./ns3 run "v2v-emergencyVehicleAlert-80211p --sumo-gui=false --met-sup=true --sumo-updates=0.1 --num-traci-clients=2"
   ```

   Con la pestaña del visor abierta arranca el lockstep: los vehículos se
   mueven y los mensajes CAM aparecen como pulsos y arcos.
3. Al terminar, las líneas `INFO-veh*` deben mostrar CAM y CPM enviados y
   recibidos, y `Average PRR` / latencia parecidos a tus corridas anteriores.
4. `curl localhost:8000/api/health` muestra `frame_ms` (coste del frame en el
   backend) y `dropped` (frames descartados por un navegador lento); ambos
   deben ser bajos.

---

## 5. Qué cambia para ti

- **Modo ligero** (casilla del panel o `http://localhost:8081/?lite=1`): menos
  GPU/CPU en portátiles con gráfica integrada. Se recuerda entre recargas.
- **Cámara con el ratón**: el modo cámara (botón 🖱 de la barra superior)
  arranca activo: arrastrar gira e inclina, Shift+arrastrar desplaza el mapa.
  Si lo desactivas, arrastrar desplaza y giras con botón derecho, Ctrl/⌘ o
  Alt/Option + arrastrar. Ya no hay pad de inclinación.
- **Recargar la página o abrir varias pestañas** no afecta a la simulación;
  una pestaña lenta ya no frena a ns-3 ni a las demás.
- **Flotas grandes** (por ejemplo
  `--mob-trace cars_120.rou.xml --sumo-config src/automotive/examples/sumo_files_v2v_map/map_120.sumo.cfg`):
  añade `--pcap=false` al `./ns3 run` para no escribir un pcap por vehículo
  (crecen con el cuadrado de la flota). Sin pcap no hay mensajes V2X en vivo
  ni replay, pero la movilidad y las métricas de `--met-sup` funcionan igual.
- **Volver al comportamiento anterior de ns-3** sin recompilar:
  `--ns3::TraciClient::UseSubscriptions=false` en el `./ns3 run`.

---

## 6. Problemas frecuentes

| Síntoma | Causa | Solución |
|---|---|---|
| No se ven vehículos, o la consola del navegador marca errores tras actualizar | `app.js` antiguo en caché, o backend y frontend de versiones distintas | Ctrl+Shift+R; comprueba que reconstruiste **las dos** imágenes (paso 2) |
| `http://localhost:8081` da error 502 | nginx arrancó antes que el backend | Espera 10-20 s y recarga |
| `/api/health` no devuelve `"proto":2` | La imagen `backend` sigue siendo la antigua | Repite el paso 2 con `--no-cache` |
| `apply-ns3-patches.sh` dice que el contenedor no está en marcha | Falta `docker compose up -d`, o estás en otra carpeta | Arranca el contenedor y ejecuta el script desde `van3twin-docker` |
| `./ns3 build` termina con `error:` | Conflicto con cambios tuyos en esos ficheros, o compilación interrumpida | Envía las 30 líneas anteriores al profesor; mientras tanto `./tools/revert-ns3-patches.sh` |
| `grep -c VehicleSnapshot` imprime 0 | Los parches no se copiaron antes de compilar | Repite el paso 3 |
| El visor dice «esperando a SUMO» | ns-3 no está corriendo, o falta `--num-traci-clients=2` | Lanza el EVA con el comando del paso 4 |
| En modo ligero el mapa se ve encogido en una esquina | Frontend anterior al 29-09 | Reconstruye el frontend (paso 2) y recarga con Ctrl+Shift+R |
| La simulación va muy lenta con muchos vehículos | pcap por nodo | `--pcap=false`; ns-3 sigue siendo el límite con cientos de vehículos |
| Disco lleno | pcaps de corridas anteriores | Borra `~/VaN3Twin/ns-3-dev/v2v-EVA-*.pcap` en el contenedor y `docker system prune` en el host |
