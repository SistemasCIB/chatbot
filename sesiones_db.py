import json
from datetime import datetime
from models import db, SesionBot


class SesionesDB:

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