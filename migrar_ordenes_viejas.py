"""
migrar_ordenes_viejas.py

Rescata órdenes médicas de citas viejas que todavía tienen el archivo
en disco (static/uploads/) pero no tienen los bytes guardados en BD
(orden_medica_datos). Se debe correr UNA SOLA VEZ, antes del próximo
deploy a producción (que borrará el disco efímero de Render Starter).

Uso:
    python migrar_ordenes_viejas.py            -> corre en modo DRY RUN (no escribe nada)
    python migrar_ordenes_viejas.py --aplicar   -> aplica los cambios de verdad
"""

import os
import sys

from app import app, db
from models import Cita

DRY_RUN = "--aplicar" not in sys.argv


def migrar():
    with app.app_context():
        # Candidatas: tienen nombre de archivo pero no tienen bytes en BD
        citas = Cita.query.filter(
            Cita.orden_medica.isnot(None),
            Cita.orden_medica != "",
            Cita.orden_medica_datos.is_(None),
        ).all()

        print(f"Citas candidatas encontradas: {len(citas)}")
        print(f"Modo: {'DRY RUN (no se escribe nada)' if DRY_RUN else 'APLICANDO CAMBIOS'}")
        print("-" * 60)

        rescatadas = 0
        no_encontradas = 0

        carpeta_uploads = os.path.join(app.root_path, "static", "uploads")

        for cita in citas:
            ruta_local = os.path.join(carpeta_uploads, cita.orden_medica)

            if os.path.exists(ruta_local):
                with open(ruta_local, "rb") as f:
                    contenido = f.read()

                print(f"  [OK] cita id={cita.id} | archivo={cita.orden_medica} | {len(contenido)} bytes")

                if not DRY_RUN:
                    cita.orden_medica_datos = contenido
                    db.session.add(cita)

                rescatadas += 1
            else:
                print(f"  [FALTA] cita id={cita.id} | archivo esperado no existe en disco: {cita.orden_medica}")
                no_encontradas += 1

        print("-" * 60)
        print(f"Total rescatables: {rescatadas}")
        print(f"Total sin archivo en disco (irrecuperables por esta vía): {no_encontradas}")

        if not DRY_RUN and rescatadas > 0:
            db.session.commit()
            print(f"\nCommit realizado. {rescatadas} citas actualizadas en BD.")
        elif DRY_RUN:
            print("\nEsto fue un DRY RUN. Nada se guardó en BD.")
            print("Si los números se ven bien, vuelve a correr con: python migrar_ordenes_viejas.py --aplicar")


if __name__ == "__main__":
    migrar()