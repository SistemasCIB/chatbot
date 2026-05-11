from app import app
from models import db, Asesor

with app.app_context():
    admin = Asesor(
        nombre='Admin',
        usuario='admin',
        rol='admin',
        activo=True
    )
    admin.set_password('cib2026')
    db.session.add(admin)
    db.session.commit()
    print("Admin creado correctamente.")
    #recordar crear admin