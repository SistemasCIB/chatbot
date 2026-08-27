import os

import requests
from dotenv import load_dotenv

load_dotenv(".env")
RECAPTCHA_SECRET_KEY = os.getenv("RECAPTCHA_SECRET_KEY")

def verificar_recaptcha(token):
    if not token:
        print("reCAPTCHA: no llegó token")
        return False
    print("Secret usado termina en:", RECAPTCHA_SECRET_KEY[-6:] if RECAPTCHA_SECRET_KEY else None)
    r = requests.post(
        'https://www.google.com/recaptcha/api/siteverify',
        data={'secret': RECAPTCHA_SECRET_KEY, 'response': token}
    )
    data = r.json()
    print("reCAPTCHA response:", data)
    return data.get('success', False)