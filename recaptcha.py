import requests
from config import RECAPTCHA_SECRET_KEY

def verificar_recaptcha(token):
    if not token:
        return False
    r = requests.post(
        'https://www.google.com/recaptcha/api/siteverify',
        data={
            'secret':   RECAPTCHA_SECRET_KEY,
            'response': token
        }
    )
    return r.json().get('success', False)