"""Il link di un brano per SoundText Mobile: lo stesso formato di mobile/share.js (#v=1&b=...&n=...).

Il testo .st, compresso (deflate senza intestazioni) e in base64 per URL, sta nel frammento del link: il browser non lo manda a
nessun server. Chi lo apre sul telefono (o in un browser del PC) ascolta il brano nell'app, lo salva fra i suoi o ne fa un remix.
"""
import base64
import zlib
from urllib.parse import quote

MOBILE_URL = "https://openssound.github.io/soundtext/"
VERSION = 1
MAX_BYTES = 1 << 20          # come nell'app: oltre, il link non si apre
LONG_LINK = 8000             # oltre, alcune app di messaggistica rischiano di tagliarlo


def make_fragment(name: str, data: bytes) -> str:
    """Il frammento (senza '#') del brano 'name' con i byte 'data' del file."""
    if len(data) > MAX_BYTES:
        raise ValueError("brano troppo grande per un link")
    packer = zlib.compressobj(9, zlib.DEFLATED, -15)
    packed = packer.compress(data) + packer.flush()
    b64 = base64.urlsafe_b64encode(packed).decode("ascii").rstrip("=")
    name_part = quote(name, safe="-_.!~*'()")          # come encodeURIComponent
    return f"v={VERSION}&b={b64}&n={name_part}"


def make_url(name: str, text: str, base: str = MOBILE_URL) -> str:
    """Il link completo del brano: apre l'app mobile con il brano pronto da ascoltare."""
    return f"{base}#{make_fragment(name, text.encode('utf-8'))}"


def read_fragment(fragment: str):
    """(nome, byte) di un frammento fatto da make_fragment o dall'app; None se non e' un brano."""
    from urllib.parse import parse_qs
    params = {k: v[0] for k, v in parse_qs(fragment.lstrip("#"), keep_blank_values=True).items()}
    if "b" not in params:
        return None
    if params.get("v") != str(VERSION):
        raise ValueError("versione del link non riconosciuta")
    raw = base64.urlsafe_b64decode(params["b"] + "=" * (-len(params["b"]) % 4))
    unpacker = zlib.decompressobj(-15)
    data = unpacker.decompress(raw, MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError("brano troppo grande")
    return params.get("n", ""), data
