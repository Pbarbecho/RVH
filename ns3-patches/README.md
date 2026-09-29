# ns3-patches — parches de rendimiento TraCI para un contenedor ya construido

Copia literal de los 8 ficheros modificados en el fork
[Pbarbecho/VaN3TwinGEO](https://github.com/Pbarbecho/VaN3TwinGEO) (commit
`9801a72`, ver `RENDIMIENTO_SUMO_GEO.md` allí). Las imágenes construidas a
partir de ahora ya los incluyen (el Dockerfile clona el fork); esta carpeta
existe para los alumnos con un volumen `ns3-workspace` anterior, donde el
árbol ns-3 no es un repo git y no se puede hacer `git pull`.

Aplicar (desde el host, contenedor en marcha): `./tools/apply-ns3-patches.sh`.
Deshacer: `./tools/revert-ns3-patches.sh`. Sin recompilar, el
comportamiento anterior se recupera con
`--ns3::TraciClient::UseSubscriptions=false` en el `./ns3 run`.

Para actualizar esta carpeta tras un cambio en el fork:
`cp` de los ficheros listados en `git diff --name-only` respetando las rutas
`src/...`.
