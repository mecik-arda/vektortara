import socket

import pytest

import vektortara.vtler.base as vt_base
from vektortara.vtler.base import TemelTarayici


class OrnekTarayici(TemelTarayici):
    veritabani_adi = "ornek"

    def parmak_izi(self) -> bool:
        return True

    def tara(self):
        return self._bulgular


@pytest.fixture(autouse=True)
def temiz_dns_onbellek():
    vt_base._DNS_ONBELLEK.clear()
    yield
    vt_base._DNS_ONBELLEK.clear()


def test_http_hostnamesi_sabit_ipe_cevrilir(monkeypatch):
    monkeypatch.setattr("socket.getaddrinfo", lambda *a, **k: [(0, 0, 0, "", ("127.0.0.9", 0))])
    tarayici = OrnekTarayici("http://ornek.test:8000")
    try:
        assert tarayici.hedef == "http://127.0.0.9:8000"
        assert tarayici._istemci.headers["Host"] == "ornek.test:8000"
    finally:
        tarayici.kapat()


def test_ipv4_basarisizsa_ipv6ya_dusulur(monkeypatch):
    def sahte_getaddrinfo(ad, port, aile, tip):
        if aile == socket.AF_INET:
            raise OSError("ipv4 yok")
        return [(0, 0, 0, "", ("fe80::1", 0))]

    monkeypatch.setattr("socket.getaddrinfo", sahte_getaddrinfo)
    tarayici = OrnekTarayici("http://ornek.test:8000")
    try:
        assert tarayici.hedef == "http://[fe80::1]:8000"
    finally:
        tarayici.kapat()


def test_coklu_adreste_ilk_ipv4_seciliyor(monkeypatch):
    def sahte_getaddrinfo(ad, port, aile, tip):
        return [(0, 0, 0, "", ("10.0.0.1", 0)), (0, 0, 0, "", ("10.0.0.2", 0))]

    monkeypatch.setattr("socket.getaddrinfo", sahte_getaddrinfo)
    tarayici = OrnekTarayici("http://ornek.test:8000")
    try:
        assert tarayici.hedef == "http://10.0.0.1:8000"
    finally:
        tarayici.kapat()


def test_ip_literal_sabitlenmez():
    tarayici = OrnekTarayici("http://10.0.0.1:8000")
    try:
        assert tarayici.hedef == "http://10.0.0.1:8000"
    finally:
        tarayici.kapat()


def test_https_varsayilanda_sabitlenmez(monkeypatch):
    cagrildi = []

    def izleyen_getaddrinfo(*a, **k):
        cagrildi.append(a)
        return [(0, 0, 0, "", ("127.0.0.9", 0))]

    monkeypatch.setattr("socket.getaddrinfo", izleyen_getaddrinfo)
    tarayici = OrnekTarayici("https://ornek.test:8443")
    try:
        assert tarayici.hedef == "https://ornek.test:8443"
        assert not cagrildi
    finally:
        tarayici.kapat()


def test_ayni_host_yonlendirmesine_izin_verilir():
    tarayici = OrnekTarayici("http://ornek.test:8000", konak_sabitle=False)
    try:
        assert (
            tarayici._guvenli_yonlendirme("http://ornek.test:8000/a", "/b")
            == "http://ornek.test:8000/b"
        )
    finally:
        tarayici.kapat()


def test_sabit_ip_sonrasi_ozgun_host_yonlendirmesine_izin(monkeypatch):
    monkeypatch.setattr("socket.getaddrinfo", lambda *a, **k: [(0, 0, 0, "", ("127.0.0.9", 0))])
    tarayici = OrnekTarayici("http://ornek.test:8000")
    try:
        assert tarayici.hedef == "http://127.0.0.9:8000"
        assert (
            tarayici._guvenli_yonlendirme(
                "http://127.0.0.9:8000/a", "http://ornek.test:8000/b"
            )
            == "http://ornek.test:8000/b"
        )
    finally:
        tarayici.kapat()


def test_farkli_host_yonlendirmesi_reddedilir():
    tarayici = OrnekTarayici("http://ornek.test:8000", konak_sabitle=False)
    try:
        assert (
            tarayici._guvenli_yonlendirme(
                "http://ornek.test:8000/a", "http://kotu-ornek.example/b"
            )
            is None
        )
    finally:
        tarayici.kapat()


def test_farkli_port_yonlendirmesi_reddedilir():
    tarayici = OrnekTarayici("http://ornek.test:8000", konak_sabitle=False)
    try:
        assert (
            tarayici._guvenli_yonlendirme(
                "http://ornek.test:8000/a", "http://ornek.test:9000/b"
            )
            is None
        )
    finally:
        tarayici.kapat()


def test_https_den_http_ye_dusus_reddedilir():
    tarayici = OrnekTarayici("https://ornek.test:8443", konak_sabitle=False)
    try:
        assert (
            tarayici._guvenli_yonlendirme(
                "https://ornek.test:8443/a", "http://ornek.test:8443/b"
            )
            is None
        )
    finally:
        tarayici.kapat()


def test_http_den_https_ye_yukseltmeye_izin_verilir():
    tarayici = OrnekTarayici("http://ornek.test:8000", konak_sabitle=False)
    try:
        assert (
            tarayici._guvenli_yonlendirme(
                "http://ornek.test:8000/a", "https://ornek.test:8000/b"
            )
            == "https://ornek.test:8000/b"
        )
    finally:
        tarayici.kapat()


def test_http_den_https_ye_farkli_porta_izin_verilmez():
    tarayici = OrnekTarayici("http://ornek.test:8000", konak_sabitle=False)
    try:
        assert (
            tarayici._guvenli_yonlendirme(
                "http://ornek.test:8000/a", "https://ornek.test:8443/b"
            )
            is None
        )
    finally:
        tarayici.kapat()


def test_yonlendirmede_kimlik_bilgisi_reddedilir():
    tarayici = OrnekTarayici("http://ornek.test:8000", konak_sabitle=False)
    try:
        assert (
            tarayici._guvenli_yonlendirme(
                "http://ornek.test:8000/a", "http://kullanici:parola@ornek.test:8000/b"
            )
            is None
        )
    finally:
        tarayici.kapat()


def test_bozuk_yonlendirme_konumu_reddedilir():
    tarayici = OrnekTarayici("http://ornek.test:8000", konak_sabitle=False)
    try:
        assert (
            tarayici._guvenli_yonlendirme(
                "http://ornek.test:8000/a", "http://ornek.test:99999/b"
            )
            is None
        )
    finally:
        tarayici.kapat()


@pytest.mark.parametrize(
    ("kod", "beklenen"),
    [
        (200, "basarili"),
        (204, "basarili"),
        (401, "yetki_reddi"),
        (403, "yetki_reddi"),
        (429, "hiz_siniri"),
        (302, "yonlendirme"),
        (500, "sunucu_hatasi"),
        (404, "diger"),
    ],
)
def test_durum_siniflari(kod, beklenen):
    assert TemelTarayici.durum_sinifi(kod) == beklenen
