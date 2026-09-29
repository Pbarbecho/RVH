#!/usr/bin/env bash
# Deshace apply-ns3-patches.sh: restaura los ficheros originales guardados en
# el contenedor y recompila. Uso: ./tools/revert-ns3-patches.sh [--no-build]
set -euo pipefail
cd "$(dirname "$0")/.."
SVC=van3twin
NS3=/home/vanet/VaN3Twin/ns-3-dev
BACKUP=/home/vanet/ns3-patches-backup.tar
docker compose exec -T "$SVC" bash -c "
  set -e; cd $NS3
  [ -f $BACKUP ] || { echo 'No hay copia de seguridad ($BACKUP): nada que revertir'; exit 1; }
  tar xf $BACKUP && rm -f $BACKUP && echo 'Originales restaurados.'"
[ "${1:-}" = "--no-build" ] || docker compose exec -T "$SVC" bash -c "cd $NS3 && ./ns3 build"
