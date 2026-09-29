#!/usr/bin/env python3
"""Cliente TraCI adicional para la simulación VaN3Twin + visor SUMO-GEO.

ns-3 lanza SUMO con --num-clients N y es el cliente 1; el visor web es el 2;
este script es el 3.  Ejecutar dentro del contenedor:

    ./ns3 run "v2v-emergencyVehicleAlert-80211p ... --num-traci-clients=3"
    python3 ~/results/traci/cliente_traci.py
"""
import os
import sys

# La librería traci de SUMO va ANTES que la carpeta del script en sys.path
sys.path.insert(0, os.path.join(os.environ.get("SUMO_HOME", "/usr/share/sumo"), "tools"))
import traci  # noqa: E402

HOST = os.environ.get("SUMO_HOST", "localhost")
ORDER = 3          # ns-3 = 1, visor = 2, este script = 3
DT = 0.5           # segundos simulados por paso del script

# Misma lógica que el visor: probar 3400-3410 porque ns-3 corre el puerto
# si el 3400 está ocupado (en la captura del taller salió en el 3401)
last_exc = None
for port in range(3400, 3411):
    try:
        traci.init(port=port, host=HOST, numRetries=1)
        print(f"Conectado a SUMO en {HOST}:{port}")
        break
    except Exception as exc:  # noqa: BLE001 - probar el siguiente puerto
        last_exc = exc
else:
    sys.exit(f"SUMO no responde en 3400-3410 (¿está ns-3 esperando clientes?)\n"
             f"Último error: {last_exc!r}")

traci.setOrder(ORDER)          # obligatorio ANTES del primer simulationStep

try:
    while traci.simulation.getMinExpectedNumber() > 0:
        # Objetivo absoluto (como el visor): ns-3 conserva su paso fino y
        # este script no le impone su ritmo
        traci.simulationStep(traci.simulation.getTime() + DT)
        t = traci.simulation.getTime()
        for vid in traci.vehicle.getIDList():
            x, y = traci.vehicle.getPosition(vid)
            v = traci.vehicle.getSpeed(vid)
            print(f"t={t:.1f} {vid} pos=({x:.1f},{y:.1f}) v={v:.1f} m/s")
        # También se puede actuar sobre SUMO, p. ej.:
        # traci.vehicle.setSpeed("veh1", 5.0)
except traci.exceptions.FatalTraCIError as exc:
    # Fin normal: al cumplirse --sim-time, ns-3 cierra SUMO y la conexión
    # se corta ("connection closed by SUMO"). No es un error.
    print(f"SUMO cerró la conexión ({exc}); fin de la simulación.")
except KeyboardInterrupt:
    print("Interrumpido por el usuario.")
finally:
    # Cerrar solo si la conexión sigue viva; en SUMO 1.12 close() falla
    # sobre una conexión ya cerrada por el servidor
    try:
        traci.close()          # si no se cierra, SUMO queda esperando a este cliente
    except Exception:
        pass
