import httpx

from vektortara.modeller import Ciddiyet
from vektortara.vtler.weaviate import WeaviateTarayici


def _anonim_sunucu(istek: httpx.Request) -> httpx.Response:
    if istek.method == "GET" and istek.url.path == "/v1/meta":
        return httpx.Response(200, json={"version": "1.27.0", "modules": {}})
    if istek.method == "GET" and istek.url.path == "/v1/schema":
        return httpx.Response(200, json={"classes": []})
    if istek.method == "GET" and istek.url.path == "/v1/.well-known/openid-configuration":
        return httpx.Response(404)
    if istek.method == "OPTIONS" and istek.url.path == "/v1/schema":
        return httpx.Response(200, headers={"access-control-allow-origin": "*"})
    return httpx.Response(404)


def _korumali_sunucu(istek: httpx.Request) -> httpx.Response:
    if istek.method == "GET" and istek.url.path == "/v1/meta":
        return httpx.Response(200, json={"version": "1.27.0", "modules": {}})
    if istek.method == "GET" and istek.url.path == "/v1/schema":
        return httpx.Response(401, json={"error": [{"message": "unauthorized"}]})
    if istek.method == "GET" and istek.url.path == "/v1/.well-known/openid-configuration":
        return httpx.Response(200, json={"issuer": "https://auth.example.com"})
    return httpx.Response(404)


def _sunucu_hatali_sunucu(istek: httpx.Request) -> httpx.Response:
    if istek.method == "GET" and istek.url.path == "/v1/meta":
        return httpx.Response(200, json={"version": "1.27.0", "modules": {}})
    if istek.method == "GET" and istek.url.path == "/v1/schema":
        return httpx.Response(503)
    return httpx.Response(404)


def _bozuk_oidc_sunucu(istek: httpx.Request) -> httpx.Response:
    if istek.method == "GET" and istek.url.path == "/v1/meta":
        return httpx.Response(200, json={"version": "1.27.0", "modules": {}})
    if istek.method == "GET" and istek.url.path == "/v1/schema":
        return httpx.Response(200, json={"classes": []})
    if istek.method == "GET" and istek.url.path == "/v1/.well-known/openid-configuration":
        return httpx.Response(200, json=[1, 2, 3])
    return httpx.Response(404)


def _tara(handler):
    tarayici = WeaviateTarayici(
        "http://ornek:8080",
        transport=httpx.MockTransport(handler),
        konak_sabitle=False,
    )
    try:
        return tarayici.tara()
    finally:
        tarayici.kapat()


def test_anonim_sunucuda_yetki_bulgusu():
    bulgular = _tara(_anonim_sunucu)
    ciddiyetler = {b.kontrol: b.ciddiyet for b in bulgular}
    assert ciddiyetler["weaviate-yetki"] == Ciddiyet.YUKSEK
    assert ciddiyetler["weaviate-oidc"] == Ciddiyet.ORTA
    assert ciddiyetler["weaviate-cors"] == Ciddiyet.ORTA


def test_korumali_sunucuda_bilgi_bulgulari():
    bulgular = _tara(_korumali_sunucu)
    ciddiyetler = {b.kontrol: b.ciddiyet for b in bulgular}
    assert ciddiyetler["weaviate-yetki"] == Ciddiyet.BILGI
    assert ciddiyetler["weaviate-oidc"] == Ciddiyet.BILGI


def test_sunucu_hatasinda_belirsiz_sonuc():
    bulgular = _tara(_sunucu_hatali_sunucu)
    ciddiyetler = {b.kontrol: b.ciddiyet for b in bulgular}
    assert ciddiyetler["weaviate-yetki"] == Ciddiyet.ORTA


def test_bozuk_oidc_yanitinda_belirsiz_sonuc():
    bulgular = _tara(_bozuk_oidc_sunucu)
    ciddiyetler = {b.kontrol: b.ciddiyet for b in bulgular}
    assert ciddiyetler["weaviate-oidc"] == Ciddiyet.ORTA


def test_parmak_izi_taniyor():
    tarayici = WeaviateTarayici(
        "http://ornek:8080",
        transport=httpx.MockTransport(_anonim_sunucu),
        konak_sabitle=False,
    )
    try:
        assert tarayici.parmak_izi()
    finally:
        tarayici.kapat()


def test_parmak_izi_tanimiyor():
    tarayici = WeaviateTarayici(
        "http://ornek:8080",
        transport=httpx.MockTransport(lambda _: httpx.Response(404)),
        konak_sabitle=False,
    )
    try:
        assert not tarayici.parmak_izi()
    finally:
        tarayici.kapat()


def test_parmak_izi_skaler_json_da_tanimiyor():
    tarayici = WeaviateTarayici(
        "http://ornek:8080",
        transport=httpx.MockTransport(lambda _: httpx.Response(200, json=42)),
        konak_sabitle=False,
    )
    try:
        assert not tarayici.parmak_izi()
    finally:
        tarayici.kapat()
