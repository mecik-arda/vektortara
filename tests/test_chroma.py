import httpx

from vektortara.modeller import Ciddiyet
from vektortara.vtler.chroma import ChromaTarayici

SURUM_YOLU = "/api/v2/version"
KALP_YOLU = "/api/v2/heartbeat"
KOLEKSIYONLAR_YOLU = "/api/v2/tenants/default_tenant/databases/default_database/collections"


def _acik_sunucu(istek: httpx.Request) -> httpx.Response:
    if istek.method == "GET" and istek.url.path == KALP_YOLU:
        return httpx.Response(200, json={"nanosecond heartbeat": 1234567890})
    if istek.method == "GET" and istek.url.path == SURUM_YOLU:
        return httpx.Response(200, json={"version": "1.5.8"})
    if istek.method == "GET" and istek.url.path == KOLEKSIYONLAR_YOLU:
        return httpx.Response(200, json=[])
    if istek.method == "OPTIONS" and istek.url.path == KALP_YOLU:
        return httpx.Response(200, headers={"access-control-allow-origin": "*"})
    return httpx.Response(404)


def _korumali_sunucu(istek: httpx.Request) -> httpx.Response:
    if istek.method == "GET" and istek.url.path == KALP_YOLU:
        return httpx.Response(200, json={"nanosecond heartbeat": 1234567890})
    if istek.method == "GET" and istek.url.path == SURUM_YOLU:
        return httpx.Response(200, json={"version": "1.5.8"})
    if istek.method == "GET" and istek.url.path == KOLEKSIYONLAR_YOLU:
        return httpx.Response(401)
    return httpx.Response(404)


def _yazma_probu_sunucu(istek: httpx.Request) -> httpx.Response:
    if istek.method == "GET" and istek.url.path == KALP_YOLU:
        return httpx.Response(200, json={"nanosecond heartbeat": 1234567890})
    if istek.method == "GET" and istek.url.path == SURUM_YOLU:
        return httpx.Response(200, json={"version": "1.5.8"})
    if istek.method == "GET" and istek.url.path == KOLEKSIYONLAR_YOLU:
        return httpx.Response(200, json=[])
    if istek.method == "POST" and istek.url.path == KOLEKSIYONLAR_YOLU:
        return httpx.Response(200, json={"name": "vektortara_probe_abcdefgh"})
    if istek.method == "DELETE" and istek.url.path.startswith(KOLEKSIYONLAR_YOLU + "/"):
        return httpx.Response(200)
    return httpx.Response(404)


def _yazma_korumali_sunucu(istek: httpx.Request) -> httpx.Response:
    if istek.method == "GET" and istek.url.path == KALP_YOLU:
        return httpx.Response(200, json={"nanosecond heartbeat": 1234567890})
    if istek.method == "GET" and istek.url.path == SURUM_YOLU:
        return httpx.Response(200, json={"version": "1.5.8"})
    if istek.method == "GET" and istek.url.path == KOLEKSIYONLAR_YOLU:
        return httpx.Response(200, json=[])
    if istek.method == "POST" and istek.url.path == KOLEKSIYONLAR_YOLU:
        return httpx.Response(401)
    return httpx.Response(404)


def _sunucu_hatali_probe(istek: httpx.Request) -> httpx.Response:
    if istek.method == "GET" and istek.url.path == KALP_YOLU:
        return httpx.Response(200, json={"nanosecond heartbeat": 1234567890})
    if istek.method == "GET" and istek.url.path == SURUM_YOLU:
        return httpx.Response(200, json={"version": "1.5.8"})
    if istek.method == "GET" and istek.url.path == KOLEKSIYONLAR_YOLU:
        return httpx.Response(200, json=[])
    if istek.method == "POST" and istek.url.path == KOLEKSIYONLAR_YOLU:
        return httpx.Response(500)
    return httpx.Response(404)


def _silme_hatali_probe(istek: httpx.Request) -> httpx.Response:
    if istek.method == "GET" and istek.url.path == KALP_YOLU:
        return httpx.Response(200, json={"nanosecond heartbeat": 1234567890})
    if istek.method == "GET" and istek.url.path == SURUM_YOLU:
        return httpx.Response(200, json={"version": "1.5.8"})
    if istek.method == "GET" and istek.url.path == KOLEKSIYONLAR_YOLU:
        return httpx.Response(200, json=[])
    if istek.method == "POST" and istek.url.path == KOLEKSIYONLAR_YOLU:
        return httpx.Response(200, json={"name": "vektortara_probe_abcdefgh"})
    if istek.method == "DELETE" and istek.url.path.startswith(KOLEKSIYONLAR_YOLU + "/"):
        return httpx.Response(500)
    return httpx.Response(404)


def _silme_404_probe(istek: httpx.Request) -> httpx.Response:
    if istek.method == "GET" and istek.url.path == KALP_YOLU:
        return httpx.Response(200, json={"nanosecond heartbeat": 1234567890})
    if istek.method == "GET" and istek.url.path == SURUM_YOLU:
        return httpx.Response(200, json={"version": "1.5.8"})
    if istek.method == "GET" and istek.url.path == KOLEKSIYONLAR_YOLU:
        return httpx.Response(200, json=[])
    if istek.method == "POST" and istek.url.path == KOLEKSIYONLAR_YOLU:
        return httpx.Response(200, json={"name": "vektortara_probe_abcdefgh"})
    if istek.method == "DELETE" and istek.url.path.startswith(KOLEKSIYONLAR_YOLU + "/"):
        return httpx.Response(404)
    return httpx.Response(404)


def _v1_sunucu(istek: httpx.Request) -> httpx.Response:
    if istek.url.path.startswith("/api/v2"):
        return httpx.Response(404)
    if istek.method == "GET" and istek.url.path == "/api/v1/heartbeat":
        return httpx.Response(200, json={"nanosecond heartbeat": 1234567890})
    if istek.method == "GET" and istek.url.path == "/api/v1/version":
        return httpx.Response(200, json={"version": "0.5.20"})
    if istek.method == "GET" and istek.url.path == "/api/v1/collections":
        return httpx.Response(200, json=[])
    return httpx.Response(404)


def _tara(handler, derin=False):
    tarayici = ChromaTarayici(
        "http://ornek:8000",
        transport=httpx.MockTransport(handler), konak_sabitle=False,
        derin=derin,
    )
    try:
        return tarayici.tara()
    finally:
        tarayici.kapat()


def test_acik_sunucuda_kritik_ve_yuksek_bulgular():
    bulgular = _tara(_acik_sunucu)
    ciddiyetler = {b.kontrol: b.ciddiyet for b in bulgular}
    assert ciddiyetler["chroma-cve"] == Ciddiyet.KRITIK
    assert ciddiyetler["chroma-yetki"] == Ciddiyet.YUKSEK
    assert ciddiyetler["chroma-cors"] == Ciddiyet.ORTA
    assert ciddiyetler["chroma-surum"] == Ciddiyet.DUSUK


def test_korumali_sunucuda_yetki_bilgisi():
    bulgular = _tara(_korumali_sunucu)
    ciddiyetler = {b.kontrol: b.ciddiyet for b in bulgular}
    assert ciddiyetler["chroma-yetki"] == Ciddiyet.BILGI


def test_derin_probe_acik_sunucuda_kritik():
    bulgular = _tara(_yazma_probu_sunucu, derin=True)
    yazma = [b for b in bulgular if b.kontrol == "chroma-yazma"]
    assert yazma and yazma[0].ciddiyet == Ciddiyet.KRITIK
    assert "temizlik:" in yazma[0].kanit


def test_probe_zaten_silinmisse_hata_uretilmez():
    bulgular = _tara(_silme_404_probe, derin=True)
    yazma = [b for b in bulgular if b.kontrol == "chroma-yazma"]
    assert any(b.ciddiyet == Ciddiyet.KRITIK for b in yazma)
    assert not any(b.ciddiyet == Ciddiyet.YUKSEK for b in yazma)


def test_delete_yonlendirilirse_temizlik_hatasi():
    def yonlendiren(istek: httpx.Request) -> httpx.Response:
        if istek.method == "GET" and istek.url.path == KALP_YOLU:
            return httpx.Response(200, json={"nanosecond heartbeat": 1234567890})
        if istek.method == "GET" and istek.url.path == SURUM_YOLU:
            return httpx.Response(200, json={"version": "1.5.8"})
        if istek.method == "GET" and istek.url.path == KOLEKSIYONLAR_YOLU:
            return httpx.Response(200, json=[])
        if istek.method == "POST" and istek.url.path == KOLEKSIYONLAR_YOLU:
            return httpx.Response(200, json={"name": "vektortara_probe_abcdefgh"})
        if istek.method == "DELETE":
            return httpx.Response(302, headers={"Location": istek.url.path})
        return httpx.Response(404)

    bulgular = _tara(yonlendiren, derin=True)
    yazma = [b for b in bulgular if b.kontrol == "chroma-yazma"]
    assert any(b.ciddiyet == Ciddiyet.KRITIK for b in yazma)
    temizlik = [b for b in yazma if b.ciddiyet == Ciddiyet.YUKSEK]
    assert temizlik and "yöntemi GET'e düşürdü" in temizlik[0].kanit


def test_yonlendirmede_post_gete_duserse_yazma_kanitlanmaz():
    gorulen = []

    def yonlendiren(istek: httpx.Request) -> httpx.Response:
        gorulen.append((istek.method, istek.url.path))
        if istek.method == "GET" and istek.url.path == KALP_YOLU:
            return httpx.Response(200, json={"nanosecond heartbeat": 1234567890})
        if istek.method == "GET" and istek.url.path == SURUM_YOLU:
            return httpx.Response(200, json={"version": "1.5.8"})
        if istek.method == "GET" and istek.url.path == KOLEKSIYONLAR_YOLU:
            return httpx.Response(200, json=[])
        if istek.method == "POST" and istek.url.path == KOLEKSIYONLAR_YOLU:
            return httpx.Response(302, headers={"Location": KOLEKSIYONLAR_YOLU})
        if istek.method == "DELETE" and istek.url.path.startswith(KOLEKSIYONLAR_YOLU + "/"):
            return httpx.Response(200)
        return httpx.Response(404)

    bulgular = _tara(yonlendiren, derin=True)
    postlar = [m for m, _ in gorulen if m == "POST"]
    assert len(postlar) == 1
    yazma = [b for b in bulgular if b.kontrol == "chroma-yazma"]
    assert yazma and all(b.ciddiyet != Ciddiyet.KRITIK for b in yazma)
    assert any(b.ciddiyet == Ciddiyet.ORTA for b in yazma)


def test_derin_probe_korumali_sunucuda_bilgi():
    bulgular = _tara(_yazma_korumali_sunucu, derin=True)
    yazma = [b for b in bulgular if b.kontrol == "chroma-yazma"]
    assert yazma and yazma[0].ciddiyet == Ciddiyet.BILGI


def test_derin_probe_sunucu_hatasinda_belirsiz_sonuc():
    bulgular = _tara(_sunucu_hatali_probe, derin=True)
    yazma = [b for b in bulgular if b.kontrol == "chroma-yazma"]
    assert yazma and yazma[0].ciddiyet == Ciddiyet.ORTA


def test_probe_silinemezse_yuksek_bulgu():
    bulgular = _tara(_silme_hatali_probe, derin=True)
    yazma = [b for b in bulgular if b.kontrol == "chroma-yazma"]
    assert any(b.ciddiyet == Ciddiyet.KRITIK for b in yazma)
    assert any(b.ciddiyet == Ciddiyet.YUKSEK for b in yazma)


def test_v1_sunucusu_v1_yollarini_kullanir():
    gorulen = []

    def kaydedici(istek: httpx.Request) -> httpx.Response:
        gorulen.append(istek.url.path)
        return _v1_sunucu(istek)

    bulgular = _tara(kaydedici)
    assert "/api/v1/collections" in gorulen
    ciddiyetler = {b.kontrol: b.ciddiyet for b in bulgular}
    assert ciddiyetler["chroma-yetki"] == Ciddiyet.YUKSEK
    assert ciddiyetler["chroma-cve"] == Ciddiyet.BILGI


def test_yonlendirme_farkli_hosta_izlenmez():
    gorulen = []

    def yonlendiren(istek: httpx.Request) -> httpx.Response:
        gorulen.append(istek.url.host)
        return httpx.Response(302, headers={"Location": "http://kotu-ornek.example/api/v2/heartbeat"})

    tarayici = ChromaTarayici(
        "http://ornek:8000",
        transport=httpx.MockTransport(yonlendiren),
        konak_sabitle=False,
    )
    try:
        assert not tarayici.parmak_izi()
    finally:
        tarayici.kapat()
    assert all(konak == "ornek" for konak in gorulen)


def test_parmak_izi_taniyor():
    tarayici = ChromaTarayici(
        "http://ornek:8000",
        transport=httpx.MockTransport(_acik_sunucu),
        konak_sabitle=False,
    )
    try:
        assert tarayici.parmak_izi()
    finally:
        tarayici.kapat()


def test_parmak_izi_tanimiyor():
    tarayici = ChromaTarayici(
        "http://ornek:8000",
        transport=httpx.MockTransport(lambda _: httpx.Response(404)),
        konak_sabitle=False,
    )
    try:
        assert not tarayici.parmak_izi()
    finally:
        tarayici.kapat()


def test_parmak_izi_liste_json_da_tanimiyor():
    def liste_donen(istek: httpx.Request) -> httpx.Response:
        if istek.url.path.endswith("/heartbeat"):
            return httpx.Response(200, json=[1, 2, 3])
        return httpx.Response(404)

    tarayici = ChromaTarayici(
        "http://ornek:8000",
        transport=httpx.MockTransport(liste_donen),
        konak_sabitle=False,
    )
    try:
        assert not tarayici.parmak_izi()
    finally:
        tarayici.kapat()
