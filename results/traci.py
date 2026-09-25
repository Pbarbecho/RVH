import os, sys
sys.path.append(os.path.join(os.environ.get("SUMO_HOME", "/usr/share/sumo"), "tools"))
import traci

HOST = os.environ.get("SUMO_HOST", "localhost")
ORDER = 3          # ns-3 = 1, visor = 2, this script = 3
DT = 0.5           # simulated seconds per step of the script

# Same logic as the visor: try 3400-3410 because ns-3 may move the port
for port in range(3400, 3411):
    try:
        traci.init(port=port, host=HOST, numRetries=1)
        print(f"Connected to SUMO on {HOST}:{port}")
        break
    except Exception:
        continue
else:
    sys.exit("SUMO not found on 3400-3410 (is ns-3 already running?)")

traci.setOrder(ORDER)          # must come BEFORE the first simulationStep

try:
    while traci.simulation.getMinExpectedNumber() > 0:
        # Absolute target (like the visor): ns-3 keeps its fine step and
        # this script does not force it to go at its own pace
        traci.simulationStep(traci.simulation.getTime() + DT)
        t = traci.simulation.getTime()
        for vid in traci.vehicle.getIDList():
            x, y = traci.vehicle.getPosition(vid)
            v = traci.vehicle.getSpeed(vid)
            print(f"t={t:.1f} {vid} pos=({x:.1f},{y:.1f}) v={v:.1f} m/s")
        # You can also act on SUMO, e.g.:
        # traci.vehicle.setSpeed("veh1", 5.0)
finally:
    traci.close()              # if you do not close, SUMO stays waiting for this client
