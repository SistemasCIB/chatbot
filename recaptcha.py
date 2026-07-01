import os

import requests
from dotenv import load_dotenv

load_dotenv(".env")
RECAPTCHA_SECRET_KEY = os.getenv("RECAPTCHA_SECRET_KEY")

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