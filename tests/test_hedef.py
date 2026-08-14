import pytest

from vektortara import hedef
from vektortara.hedef import HedefHatasi


@pytest.mark.parametrize(
    ("girdi", "port", "beklenen"),
    [
        ("localhost:8000", None, "http://localhost:8000"),
        ("localhost", None, "http://localhost"),
        ("https://db.example.com", None, "https://db.example.com"),
        ("localhost", 8000, "http://localhost:8000"),
        ("http://localhost:9000", 8000, "http://localhost:9000"),
        ("http://localhost:9000/x", None, "http://localhost:9000/x"),
        ("::1", None, "http://[::1]"),
        ("[::1]:8000", None, "http://[::1]:8000"),
        ("https://[2001:db8::1]", None, "https://[2001:db8::1]"),
    ],
)
def test_hedef_olustur(girdi, port, beklenen):
    assert hedef.hedef_olustur(girdi, port) == beklenen


@pytest.mark.parametrize(
    ("girdi", "beklenen"),
    [
        ("localhost:8000", True),
        ("localhost", False),
        ("https://db.example.com", False),
        ("https://db.example.com:443", True),
        ("::1", False),
    ],
)
def test_port_belli_mi(girdi, beklenen):
    assert hedef.port_belli_mi(girdi) is beklenen


@pytest.mark.parametrize(
    "girdi",
    [
        "http://kullanici:parola@ornek.com",
        "kullanici:parola@ornek.com:8000",
        "ftp://ornek.com",
        "",
    ],
)
def test_hatali_hedefler_reddedilir(girdi):
    with pytest.raises(HedefHatasi):
        hedef.hedef_olustur(girdi)


@pytest.mark.parametrize("port", [0, -1, 70000])
def test_gecersiz_port_reddedilir(port):
    with pytest.raises(HedefHatasi):
        hedef.hedef_olustur("localhost", port)


def test_url_icinde_gecersiz_port_reddedilir():
    with pytest.raises(HedefHatasi):
        hedef.hedef_olustur("http://localhost:99999")


def test_sorgu_parametreli_hedef_reddedilir():
    with pytest.raises(HedefHatasi):
        hedef.hedef_olustur("http://ornek.com:8000/?token=gizli-deger")
