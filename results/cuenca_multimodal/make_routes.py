#!/usr/bin/env python3
"""Ensambla las rutas del escenario multimodal de Cuenca para ns-3 + SUMO.

Entrada (generada por build_multimodal.sh con randomTrips/duarouter):
  _cars.rou.xml   coches/motos/buses (tipo car_mix)
  _bikes.rou.xml  bicicletas
  _peds.rou.xml   peatones (personas)
y la red + las paradas de transporte público (ptstops) para trazar el tranvía.

Salida:
  cuenca_mm.rou.xml            vehículos (coches, motos, buses, bicis,
                               tranvías y ambulancias) -> ns-3 + SUMO
  cuenca_mm.peatones.rou.xml   personas a pie -> SOLO SUMO/visor (ver README)

Reglas impuestas por VaN3Twin (ejemplo v2v-emergencyVehicleAlert-80211p):
  * ns-3 crea un nodo por cada elemento <vehicle> del .rou.xml (XPath
    //vehicle): nada de <flow>, cada vehículo explícito.
  * la aplicación calcula el StationID con std::stol(id.substr(3)): todos
    los ids deben ser veh<N>.
  * las personas también se convierten en nodos ns-3 y NO se cuentan en el
    .rou.xml -> "Node Pool empty!". Por eso van en un fichero aparte.

Uso: python3 make_routes.py <red.net.xml> <ptstops.xml> [--tram-headway 300]
     [--end 900] [--emergency 3] [--seed 42]
"""
import argparse
import os
import random
import sys
import xml.etree.ElementTree as ET

if "SUMO_HOME" in os.environ:
    sys.path.append(os.path.join(os.environ["SUMO_HOME"], "tools"))
import sumolib  # noqa: E402

VTYPES = """\
    <!-- Tráfico general: 75 % turismos, 18 % motos, 7 % buses -->
    <vTypeDistribution id="car_mix">
        <vType id="passenger" vClass="passenger" probability="0.75" accel="2.6" decel="4.5" maxSpeed="13.89" color="0.85,0.85,0.88"/>
        <vType id="motorcycle" vClass="motorcycle" probability="0.18" accel="3.5" decel="5.0" maxSpeed="16.67" length="2.2" width="0.8"/>
        <vType id="bus" vClass="bus" probability="0.07" accel="1.2" decel="3.0" maxSpeed="11.11" length="12" width="2.5"/>
    </vTypeDistribution>
    <!-- Bicicletas: circulan por ciclovías, carriles bici y calles -->
    <vType id="bicycle" vClass="bicycle" accel="1.2" decel="3.0" maxSpeed="5.56" length="1.7" width="0.65" speedDev="0.1"/>
    <!-- Tranvía de los Cuatro Ríos (Alstom Citadis 302: 32,5 m x 2,65 m) -->
    <vType id="tram" vClass="tram" guiShape="rail/railcar" accel="1.0" decel="1.3" maxSpeed="13.89" length="32.5" width="2.65" minGap="5" color="0.80,0.10,0.15"/>
    <!-- Vehículo de emergencia: activa la aplicación EVA (stationType specialVehicle) -->
    <vType id="emergency" vClass="emergency" guiShape="emergency" accel="3.0" decel="6.0" maxSpeed="19.44" speedFactor="1.3" color="1,1,1">
        <param key="has.bluelight.device" value="true"/>
    </vType>
"""


def read_vehicles(path):
    """[(depart, type, edges, stops)] de un .rou.xml de duarouter."""
    out = []
    if not os.path.exists(path):
        return out
    for v in ET.parse(path).getroot().iter("vehicle"):
        r = v.find("route")
        if r is None:
            continue
        out.append({"depart": float(v.get("depart", "0")), "type": v.get("type"),
                    "edges": r.get("edges"), "stops": []})
    return out


def tram_lines(net, stops_path):
    """Líneas de tranvía: para cada arista de vía sin predecesor, el
    recorrido más largo hasta una arista sin sucesor, con sus paradas."""
    tram = [e for e in net.getEdges() if e.getFunction() == ""
            and any(l.allows("tram") for l in e.getLanes())]
    ids = {e.getID() for e in tram}
    sources = [e for e in tram if not any(i.getID() in ids for i in e.getIncoming())]
    sinks = [e for e in tram if not any(o.getID() in ids for o in e.getOutgoing())]
    stops = []
    if os.path.exists(stops_path):
        for s in ET.parse(stops_path).getroot():
            if s.tag in ("trainStop", "busStop") and s.get("lane"):
                edge = s.get("lane").rsplit("_", 1)[0]
                if edge in ids:
                    stops.append((s.tag, s.get("id"), edge, float(s.get("endPos", "0")),
                                  s.get("name", "")))
    lines = []
    for src in sources:
        best = None
        for dst in sinks:
            path, cost = net.getShortestPath(src, dst, vClass="tram")
            if path and (best is None or cost > best[1]):
                best = (path, cost)
        if not best or best[1] < 300:
            continue
        edges = [e.getID() for e in best[0]]
        order = {e: i for i, e in enumerate(edges)}
        st = sorted([s for s in stops if s[2] in order], key=lambda s: (order[s[2]], s[3]))
        lines.append({"edges": " ".join(edges), "length": best[1], "stops": st})
    return lines


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("net")
    ap.add_argument("ptstops")
    ap.add_argument("--cars", default="_cars.rou.xml")
    ap.add_argument("--bikes", default="_bikes.rou.xml")
    ap.add_argument("--peds", default="_peds.rou.xml")
    ap.add_argument("--prefix", default="cuenca_mm")
    ap.add_argument("--end", type=float, default=900, help="última salida (s)")
    ap.add_argument("--tram-headway", type=float, default=300, help="frecuencia por sentido (s)")
    ap.add_argument("--tram-dwell", type=float, default=20, help="tiempo en parada (s)")
    ap.add_argument("--emergency", type=int, default=3, help="ambulancias")
    ap.add_argument("--seed", type=int, default=42)
    a = ap.parse_args()
    rnd = random.Random(a.seed)
    net = sumolib.net.readNet(a.net)

    cars = read_vehicles(a.cars)
    for v in cars:
        v["type"] = "car_mix"
    bikes = read_vehicles(a.bikes)
    for v in bikes:
        v["type"] = "bicycle"

    trams = []
    lines = tram_lines(net, a.ptstops)
    for k, ln in enumerate(lines):
        t = k * a.tram_headway / max(len(lines), 1)     # sentidos desfasados
        while t <= a.end:
            trams.append({"depart": t, "type": "tram", "edges": ln["edges"], "stops": ln["stops"]})
            t += a.tram_headway

    # ambulancias: copian el recorrido de coches largos, repartidas en el tiempo
    emerg = []
    def route_len(edges):
        return sum(net.getEdge(e).getLength() for e in edges.split())
    longs = sorted(cars, key=lambda v: -route_len(v["edges"]))[:max(a.emergency * 4, 1)]
    rnd.shuffle(longs)
    for i in range(min(a.emergency, len(longs))):
        emerg.append({"depart": round((i + 0.5) * a.end / a.emergency), "type": "emergency",
                      "edges": longs[i]["edges"], "stops": []})

    allv = sorted(cars + bikes + trams + emerg, key=lambda v: (v["depart"], v["type"]))
    rou = f"{a.prefix}.rou.xml"
    with open(rou, "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write("<!-- Generado por make_routes.py (escenario multimodal de Cuenca).\n"
                f"     {len(cars)} coches/motos/buses, {len(bikes)} bicicletas, {len(trams)} tranvías,\n"
                f"     {len(emerg)} ambulancias = {len(allv)} vehículos (= nodos ns-3). -->\n")
        f.write('<routes xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
                'xsi:noNamespaceSchemaLocation="http://sumo.dlr.de/xsd/routes_file.xsd">\n')
        f.write(VTYPES)
        for i, v in enumerate(allv):
            extra = ' departLane="best" departSpeed="max"' if v["type"] != "tram" else ""
            f.write(f'    <vehicle id="veh{i}" type="{v["type"]}" depart="{v["depart"]:.2f}"{extra}>\n')
            f.write(f'        <route edges="{v["edges"]}"/>\n')
            for tag, sid, _edge, _pos, name in v["stops"]:
                attr = "trainStop" if tag == "trainStop" else "busStop"
                f.write(f'        <stop {attr}="{sid}" duration="{a.tram_dwell:g}"/>'
                        f'  <!-- {name} -->\n')
            f.write("    </vehicle>\n")
        f.write("</routes>\n")

    peds = 0
    if os.path.exists(a.peds):
        root = ET.parse(a.peds).getroot()
        persons = sorted(root.iter("person"), key=lambda p: float(p.get("depart", "0")))
        with open(f"{a.prefix}.peatones.rou.xml", "w", encoding="utf-8") as f:
            f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
            f.write("<!-- Peatones del escenario multimodal. SOLO para SUMO/visor: el ejemplo\n"
                    "     EVA de ns-3 convertiría cada persona en un nodo no contado. -->\n")
            f.write("<routes>\n")
            for i, p in enumerate(persons):
                p.set("id", f"ped{i}")
                p.tail = "\n"
                for c in p:
                    c.tail = "\n        "
                f.write("    " + ET.tostring(p, encoding="unicode").rstrip() + "\n")
                peds += 1
            f.write("</routes>\n")

    print(f"{rou}: {len(allv)} vehículos -> coches/motos/buses {len(cars)}, bicis {len(bikes)}, "
          f"tranvías {len(trams)} ({len(lines)} líneas), ambulancias {len(emerg)}")
    for ln in lines:
        print(f"  línea tranvía {ln['length']:.0f} m, {len(ln['stops'])} paradas: "
              + ", ".join(s[4] for s in ln["stops"]))
    print(f"{a.prefix}.peatones.rou.xml: {peds} peatones")


if __name__ == "__main__":
    main()
