import json
from datetime import datetime
from models import db, SesionBot


class SessionProxy(dict):
    def __init__(self, parent, numero, datos):
        super().__init__(datos)
        self._parent = parent
        self._numero = numero

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        self._parent[self._numero] = dict(self)

    def __delitem__(self, key):
        super().__delitem__(key)
        self._parent[self._numero] = dict(self)


class SesionesDB:

    def __contains__(self, numero):
        return SesionBot.query.filter_by(numero=numero).first() is not None

    def __getitem__(self, numero):

        s = SesionBot.query.filter_by(numero=numero).first()

        if s is None:
            s = SesionBot(
                numero=numero,
                datos="{}"
            )
            db.session.add(s)
            db.session.commit()

        return SessionProxy(
            self,
            numero,
            s.as_dict()
        )

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

        s = SesionBot.query.filter_by(numero=numero).first()

        if s is None:
            s = SesionBot(
                numero=numero,
                datos="{}"
            )
            db.session.add(s)

        datos = s.as_dict()
        datos[key] = value

        s.set_datos(datos)
        s.actualizada_en = datetime.utcnow()

        try:
            db.session.commit()
        except:
            db.session.rollback()
            raise