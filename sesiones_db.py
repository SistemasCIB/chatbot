# sesiones_db.py
import json
from models import db, SesionBot
from datetime import datetime

class SesionesDB:
    """Wrapper que imita dict pero persiste en BD."""

    def __contains__(self, numero):
        return SesionBot.query.filter_by(numero=numero).first() is not None

    def __getitem__(self, numero):
        s = SesionBot.query.filter_by(numero=numero).first()
        if s is None:
            raise KeyError(numero)
        return s.as_dict()

    def __setitem__(self, numero, valor):
        s = SesionBot.query.filter_by(numero=numero).first()
        if s is None:
            s = SesionBot(numero=numero)
            db.session.add(s)
        s.set_datos(valor)
        s.actualizada_en = datetime.utcnow()
        try:
            db.session.commit()
        except:
            db.session.rollback()
            raise

    def __delitem__(self, numero):
        s = SesionBot.query.filter_by(numero=numero).first()
        if s:
            db.session.delete(s)
            try:
                db.session.commit()
            except:
                db.session.rollback()

    def get(self, numero, default=None):
        s = SesionBot.query.filter_by(numero=numero).first()
        if s is None:
            return default
        return s.as_dict()

    def update_key(self, numero, key, value):
        """Actualiza un solo campo de la sesión sin reescribir todo."""
        s = SesionBot.query.filter_by(numero=numero).first()
        if s is None:
            s = SesionBot(numero=numero)
            db.session.add(s)
        d = s.as_dict()
        d[key] = value
        s.set_datos(d)
        s.actualizada_en = datetime.utcnow()
        try:
            db.session.commit()
        except:
            db.session.rollback()
            raise