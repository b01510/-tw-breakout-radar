"""Single-owner login. The dashboard and every data endpoint require a session."""
import base64, hashlib, hmac, json, os, secrets, time
from http.cookies import SimpleCookie

COOKIE='radar_session'
TTL=12*60*60

def password_hash(password):
    salt=secrets.token_bytes(16)
    derived=hashlib.scrypt(password.encode(),salt=salt,n=16384,r=8,p=1)
    return 'scrypt$'+salt.hex()+'$'+derived.hex()

def verify_password(password,stored):
    try:
        kind,salt,expected=stored.split('$')
        if kind!='scrypt': return False
        actual=hashlib.scrypt(password.encode(),salt=bytes.fromhex(salt),n=16384,r=8,p=1).hex()
        return hmac.compare_digest(actual,expected)
    except (ValueError,TypeError):return False

def issue_session(secret):
    payload=base64.urlsafe_b64encode(json.dumps({'expires':int(time.time())+TTL,'nonce':secrets.token_hex(16)}).encode()).decode()
    signature=hmac.new(secret.encode(),payload.encode(),hashlib.sha256).hexdigest()
    return payload+'.'+signature

def valid_session(header,secret):
    try:
        cookies=SimpleCookie();cookies.load(header or '')
        token=cookies[COOKIE].value
        payload,sig=token.split('.')
        if not hmac.compare_digest(sig,hmac.new(secret.encode(),payload.encode(),hashlib.sha256).hexdigest()):return False
        return json.loads(base64.urlsafe_b64decode(payload))['expires']>time.time()
    except (KeyError,ValueError,TypeError):return False
