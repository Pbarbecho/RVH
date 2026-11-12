#!/usr/bin/env bash
# =============================================================================
# apply-ns3-patches.sh — aplica los parches de VaN3TwinGEO (rendimiento
# TraCI + correcciones de noviembre 2026: SUMO ya no queda huérfano, CPM con
# tranvías, StationType por vClass) a un contenedor van3twin YA construido.
#
# Por qué existe: el árbol ns-3 del volumen ns3-workspace NO es un repo git
# (sandbox_builder.sh borra .git al montar el sandbox), así que no se puede
# hacer `git pull` dentro del contenedor. Este script copia los 8 ficheros
# parcheados (carpeta ns3-patches/, copia literal del fork) dentro del
# contenedor, guarda los originales (solo los que aún no estaban guardados)
# y recompila. Se puede ejecutar varias veces: si el contenedor ya tiene esta
# versión de los parches, no hace nada.
#
# Uso, desde la carpeta van3twin-docker del host (Mac/PC), con el contenedor
# arrancado (docker compose up -d):
#   ./tools/apply-ns3-patches.sh            # copia + ./ns3 build (10-30 min)
#   ./tools/apply-ns3-patches.sh --no-build # solo copia
# Deshacer: ./tools/revert-ns3-patches.sh
# =============================================================================
set -euo pipefail
cd "$(dirname "$0")/.."

SVC=van3twin
NS3=/home/vanet/VaN3Twin/ns-3-dev
BACKUP=/home/vanet/ns3-patches-backup.tar
BUILD=1
[ "${1:-}" = "--no-build" ] && BUILD=0

if ! docker compose ps --status running --services 2>/dev/null | grep -qx "$SVC"; then
  echo "El contenedor '$SVC' no está en marcha: docker compose up -d" >&2
  exit 1
fi

FILES=$(cd ns3-patches && find src -type f | sort)
# marca de versión: una cadena que solo existe en ESTA versión de los parches
MARK='KillSumo'
echo "Ficheros a parchear:"; echo "$FILES" | sed 's/^/  /'

if docker compose exec -T "$SVC" bash -c "grep -q '$MARK' $NS3/src/traci/model/traci-client.h" 2>/dev/null; then
  echo "El contenedor ya tiene esta versión de los parches: nada que hacer."
  exit 0
fi

# 1) copia de seguridad de los originales: solo la primera vez por fichero
#    (un fichero que entra en una versión posterior de los parches se añade al
#    tar existente; --ignore-failed-read tolera ficheros aún inexistentes)
docker compose exec -T "$SVC" bash -c "
  set -e; cd $NS3
  if [ ! -f $BACKUP ]; then
    tar cf $BACKUP --ignore-failed-read $(echo $FILES | tr '\n' ' '); echo 'Originales guardados en $BACKUP'
  else
    for f in $(echo $FILES | tr '\n' ' '); do
      tar tf $BACKUP | grep -qx \"\$f\" || { tar rf $BACKUP --ignore-failed-read \"\$f\" && echo \"Original añadido a la copia: \$f\"; }
    done
  fi"

# 2) copiar los ficheros parcheados (docker cp los deja de root: devolverlos a vanet)
docker compose cp ns3-patches/src/. "$SVC:$NS3/src/"
docker compose exec -T -u root "$SVC" bash -c "cd $NS3 && chown -R vanet:vanet src/traci src/automotive"
docker compose exec -T "$SVC" bash -c "cd $NS3 && grep -q '$MARK' src/traci/model/traci-client.h && echo 'Parches copiados.'"

# 3) recompilar
if [ "$BUILD" = 1 ]; then
  echo "Compilando (./ns3 build), 10-30 minutos..."
  docker compose exec -T "$SVC" bash -c "cd $NS3 && ./ns3 build"
  echo "Listo. Prueba: ./ns3 run \"v2v-emergencyVehicleAlert-80211p --sumo-gui=false --met-sup=true --sumo-updates=0.1 --num-traci-clients=2\""
else
  echo "Copiado sin compilar: recuerda ./ns3 build dentro del contenedor."
fi
