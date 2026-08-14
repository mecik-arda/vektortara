import httpx

from vektortara.modeller import Ciddiyet
from vektortara.vtler.qdrant import QdrantTarayici


def _acik_sunucu(istek: httpx.Request) -> httpx.Response:
    if istek.method == "GET" and istek.url.path == "/":
        return httpx.Response(200, text="<html><title>qdrant - vector search engine</title></html>")
    if istek.method == "GET" and istek.url.path == "/telemetry":
        return httpx.Response(
            200,
            json={"app": {"name": "qdrant - vector search engine", "version": "1.13.4"}},
        )
    if istek.method == "GET" and istek.url.path == "/collections":
        return httpx.Response(200, json={"result": {"collections": []}, "status": "ok", "time": 0.001})
    if istek.method == "OPTIONS" and istek.url.path == "/collections":
        return httpx.Response(200, headers={"access-control-allow-origin": "*"})
    return httpx.Response(404)


def _anahtarli_sunucu(istek: httpx.Request) -> httpx.Response:
    if istek.method == "GET" and istek.url.path == "/":
        return httpx.Response(200, text="<html><title>qdrant - vector search engine</title></html>")
    if istek.method == "GET" and istek.url.path == "/telemetry":
        return httpx.Response(
            200,
            json={"app": {"name": "qdrant - vector search engine", "version": "1.13.4"}},
        )
    if istek.method == "GET" and istek.url.path == "/collections":
        return httpx.Response(403, json={"status": {"error": "Unauthorized"}})
    return httpx.Response(404)


def _sunucu_hatali_sunucu(istek: httpx.Request) -> httpx.Response:
    if istek.method == "GET" and istek.url.path == "/":
        return httpx.Response(200, text="<html><title>qdrant - vector search engine</title></html>")
    if istek.method == "GET" and istek.url.path == "/collections":
        return httpx.Response(503)
    return httpx.Response(404)


def _bozuk_telemetri_sunucu(istek: httpx.Request) -> httpx.Response:
    if istek.method == "GET" and istek.url.path == "/":
        return httpx.Response(200, text="<html><title>qdrant - vector search engine</title></html>")
    if istek.method == "GET" and istek.url.path == "/telemetry":
        return httpx.Response(200, text="json değil")
    if istek.method == "GET" and istek.url.path == "/collections":
        return httpx.Response(200, json={"result": {"collections": []}, "status": "ok"})
    return httpx.Response(404)


def _tara(handler):
    tarayici = QdrantTarayici(
        "http://ornek:6333",
        transport=httpx.MockTransport(handler),
        konak_sabitle=False,
    )
    try:
        return tarayici.tara()
    finally:
        tarayici.kapat()


def test_acik_sunucuda_yetki_bulgusu():
    bulgular = _tara(_acik_sunucu)
    ciddiyetler = {b.kontrol: b.ciddiyet for b in bulgular}
    assert ciddiyetler["qdrant-yetki"] == Ciddiyet.YUKSEK
    assert ciddiyetler["qdrant-cors"] == Ciddiyet.ORTA
    assert ciddiyetler["qdrant-surum"] == Ciddiyet.DUSUK


def test_anahtarli_sunucuda_bilgi_bulgusu():
    bulgular = _tara(_anahtarli_sunucu)
    ciddiyetler = {b.kontrol: b.ciddiyet for b in bulgular}
    assert ciddiyetler["qdrant-yetki"] == Ciddiyet.BILGI


def test_sunucu_hatasinda_belirsiz_sonuc():
    bulgular = _tara(_sunucu_hatali_sunucu)
    ciddiyetler = {b.kontrol: b.ciddiyet for b in bulgular}
    assert ciddiyetler["qdrant-yetki"] == Ciddiyet.ORTA


def test_bozuk_telemetride_belirsiz_sonuc():
    bulgular = _tara(_bozuk_telemetri_sunucu)
    ciddiyetler = {b.kontrol: b.ciddiyet for b in bulgular}
    assert ciddiyetler["qdrant-surum"] == Ciddiyet.ORTA


def test_parmak_izi_taniyor():
    tarayici = QdrantTarayici(
        "http://ornek:6333",
        transport=httpx.MockTransport(_acik_sunucu),
        konak_sabitle=False,
    )
    try:
        assert tarayici.parmak_izi()
    finally:
        tarayici.kapat()


def test_parmak_izi_tanimiyor():
    tarayici = QdrantTarayici(
        "http://ornek:6333",
        transport=httpx.MockTransport(lambda _: httpx.Response(404)),
        konak_sabitle=False,
    )
    try:
        assert not tarayici.parmak_izi()
    finally:
        tarayici.kapat()
