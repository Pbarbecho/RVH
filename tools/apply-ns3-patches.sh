#!/usr/bin/env bash
# =============================================================================
# apply-ns3-patches.sh — aplica los parches de rendimiento TraCI de
# VaN3TwinGEO (commit 9801a72) a un contenedor van3twin YA construido.
#
# Por qué existe: el árbol ns-3 del volumen ns3-workspace NO es un repo git
# (sandbox_builder.sh borra .git al montar el sandbox), así que no se puede
# hacer `git pull` dentro del contenedor. Este script copia los 8 ficheros
# parcheados (carpeta ns3-patches/, copia literal del fork) dentro del
# contenedor, guarda los originales y recompila.
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
echo "Ficheros a parchear:"; echo "$FILES" | sed 's/^/  /'

# 1) copia de seguridad de los originales (solo la primera vez)
docker compose exec -T "$SVC" bash -c "
  set -e; cd $NS3
  if [ ! -f $BACKUP ]; then tar cf $BACKUP $(echo $FILES | tr '\n' ' '); echo 'Originales guardados en $BACKUP'; fi"

# 2) copiar los ficheros parcheados
docker compose cp ns3-patches/src/. "$SVC:$NS3/src/"
docker compose exec -T "$SVC" bash -c "cd $NS3 && grep -q 'VehicleSnapshot' src/traci/model/traci-client.h && echo 'Parches copiados.'"

# 3) recompilar
if [ "$BUILD" = 1 ]; then
  echo "Compilando (./ns3 build), 10-30 minutos..."
  docker compose exec -T "$SVC" bash -c "cd $NS3 && ./ns3 build"
  echo "Listo. Prueba: ./ns3 run \"v2v-emergencyVehicleAlert-80211p --sumo-gui=false --met-sup=true --sumo-updates=0.1 --num-traci-clients=2\""
fi
