#!/usr/bin/env bash
# Regenera el escenario multimodal de Cuenca (centro histórico) a partir del
# extracto OSM ../cuenca/map.osm: calles, aceras, pasos de cebra, calles
# peatonales, ciclovías/carriles bici y el Tranvía de los Cuatro Ríos.
#
# Pensado para SUMO 1.12 (el del contenedor van3twin). Dentro del contenedor:
#   cd ~/results/cuenca_multimodal && ./build_multimodal.sh
# En el Mac/PC (pip install eclipse-sumo==1.12.0):
#   export SUMO_HOME=$(python3 -c "import os,sumo;print(os.path.dirname(sumo.__file__))")
#   ./build_multimodal.sh
#
# Variables opcionales: END (última salida, s; 900), CAR_PERIOD (s entre
# coches; 4), BIKE_PERIOD (20), PED_PERIOD (2), TRAM_HEADWAY (300), SEED (42)
set -euo pipefail
: "${SUMO_HOME:=/usr/share/sumo}"
export SUMO_HOME
export PATH="$SUMO_HOME/bin:$PATH"
PY="$(command -v python3)"
T="$SUMO_HOME/data/typemap"
HERE="$(cd "$(dirname "$0")" && pwd)"
cd "$HERE"
OSM="${OSM:-../cuenca/map.osm}"
END="${END:-900}"; SEED="${SEED:-42}"
CAR_PERIOD="${CAR_PERIOD:-4}"; BIKE_PERIOD="${BIKE_PERIOD:-20}"; PED_PERIOD="${PED_PERIOD:-2}"
TRAM_HEADWAY="${TRAM_HEADWAY:-300}"
N=cuenca_mm
echo "SUMO: $(netconvert --version | head -1)   OSM: $OSM"

echo "1/4  Red multimodal…"
# typemaps Pedestrians + Bicycle: footway/pedestrian/steps/path y cycleway
#   como aristas propias; --osm.sidewalks/--osm.bike-access usan las
#   etiquetas sidewalk=* y cycleway=lane/track de OSM; --sidewalks.guess y
#   --crossings.guess completan aceras y cebras donde OSM no las trae.
# --ptstop-output/--ptline-output: paradas y líneas del tranvía.
# (NO usar --osm.crossings: no existe en SUMO 1.12.)
netconvert --osm-files "$OSM" \
  --type-files "$T/osmNetconvert.typ.xml,$T/osmNetconvertPedestrians.typ.xml,$T/osmNetconvertBicycle.typ.xml" \
  --osm.sidewalks --osm.bike-access \
  --sidewalks.guess --crossings.guess --walkingareas \
  --ptstop-output "$N.ptstops.xml" --ptline-output "$N.ptlines.xml" --ptline-clean-up \
  --geometry.remove --ramps.guess --roundabouts.guess --junctions.join \
  --tls.guess-signals --tls.discard-simple --tls.join \
  --remove-edges.isolated --output.street-names \
  --no-warnings -o "$N.net.xml"

echo "2/4  Polígonos (edificios con altura, zonas verdes, agua, árboles)…"
polyconvert --osm-files "$OSM" --net-file "$N.net.xml" \
  --type-file "$T/osmPolyconvert.typ.xml" --osm.keep-full-type \
  --no-warnings -o "$N.poly.xml"
"$PY" enrich_heights.py "$OSM" "$N.poly.xml"

echo "3/4  Demanda (coches, bicis, peatones)…"
RT="$SUMO_HOME/tools/randomTrips.py"
"$PY" "$RT" -n "$N.net.xml" -a "$N.vtypes.add.xml" -o _cars.trips.xml -r _cars.rou.xml \
  --vclass passenger -t 'type="car_mix"' --prefix car \
  -b 0 -e "$END" -p "$CAR_PERIOD" --fringe-factor 5 --min-distance 400 \
  --remove-loops --validate --seed "$SEED"
"$PY" "$RT" -n "$N.net.xml" -a "$N.vtypes.add.xml" -o _bikes.trips.xml -r _bikes.rou.xml \
  --vclass bicycle -t 'type="bicycle"' --prefix bike \
  -b 0 -e "$END" -p "$BIKE_PERIOD" --min-distance 300 \
  --remove-loops --validate --seed "$((SEED + 1))"
"$PY" "$RT" -n "$N.net.xml" -o _peds.trips.xml -r _peds.rou.xml \
  --pedestrians --prefix ped \
  -b 0 -e "$END" -p "$PED_PERIOD" --min-distance 200 --max-distance 700 --seed "$((SEED + 2))"

echo "4/4  Tranvía, ambulancias y numeración veh<N>…"
"$PY" make_routes.py "$N.net.xml" "$N.ptstops.xml" --end "$END" \
  --tram-headway "$TRAM_HEADWAY" --seed "$SEED"
rm -f _cars.* _bikes.* _peds.* "$N".*.alt.xml
echo "OK. ns-3: $N.sumocfg · SUMO/visor con peatones: ${N}_peatones.sumocfg"
