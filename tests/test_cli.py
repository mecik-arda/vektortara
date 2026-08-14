import json

import pytest

import vektortara.cli as cli
from vektortara.modeller import Bulgu, Ciddiyet
from vektortara.vtler.base import TaramaHatasi


class SahteTarayici:
    veritabani_adi = "sahte"
    varsayilan_port = 1234
    sonuc: list[Bulgu] = []
    hata: Exception | None = None

    def __init__(self, hedef, **kwargs):
        self.hedef = hedef

    def parmak_izi(self):
        return True

    def tara(self):
        if self.hata:
            raise self.hata
        return list(self.sonuc)

    def kapat(self):
        pass


@pytest.fixture(autouse=True)
def sahte_tarayici(monkeypatch):
    SahteTarayici.sonuc = []
    SahteTarayici.hata = None
    monkeypatch.setitem(cli.TARAYICILAR, "chroma", SahteTarayici)


def _bulgu(ciddiyet):
    return Bulgu(ciddiyet, "deneme", "detay", "oneri", "kontrol", "sahte")


def test_bulgu_varsa_cikis_1():
    SahteTarayici.sonuc = [_bulgu(Ciddiyet.YUKSEK)]
    with pytest.raises(SystemExit) as cikis:
        cli.main(["tara", "localhost:1", "--tur", "chroma"])
    assert cikis.value.code == 1


def test_sadece_bilgi_varsa_cikis_0():
    SahteTarayici.sonuc = [_bulgu(Ciddiyet.BILGI)]
    with pytest.raises(SystemExit) as cikis:
        cli.main(["tara", "localhost:1", "--tur", "chroma"])
    assert cikis.value.code == 0


def test_tarama_hatasinda_cikis_2():
    SahteTarayici.hata = TaramaHatasi("sahte bağlantı hatası")
    with pytest.raises(SystemExit) as cikis:
        cli.main(["tara", "localhost:1", "--tur", "chroma"])
    assert cikis.value.code == 2


def test_kimlik_bilgili_hedef_reddedilir():
    with pytest.raises(SystemExit) as cikis:
        cli.main(["tara", "kullanici:parola@ornek.com"])
    assert cikis.value.code == 2


def test_json_ciktisi(capsys):
    SahteTarayici.sonuc = [_bulgu(Ciddiyet.YUKSEK)]
    with pytest.raises(SystemExit):
        cli.main(["tara", "localhost:1", "--tur", "chroma", "--json"])
    cikti = json.loads(capsys.readouterr().out)
    assert cikti["veritabani"] == "sahte"
    assert cikti["bulgu_sayisi"] == 1
    assert cikti["bulgular"][0]["ciddiyet"] == "YÜKSEK"
    assert cikti["tls_dogrulamasi"] is True


def test_json_tls_dogrulamasi_kapali(capsys):
    SahteTarayici.sonuc = [_bulgu(Ciddiyet.BILGI)]
    with pytest.raises(SystemExit):
        cli.main(["tara", "localhost:1", "--tur", "chroma", "--json", "--guvensiz-tls"])
    cikti = json.loads(capsys.readouterr().out)
    assert cikti["tls_dogrulamasi"] is False


def test_beklenmeyen_hata_iz_birakmaz(capsys):
    SahteTarayici.hata = RuntimeError("beklenmedik durum")
    with pytest.raises(SystemExit) as cikis:
        cli.main(["tara", "localhost:1", "--tur", "chroma"])
    assert cikis.value.code == 2
    cikti = capsys.readouterr()
    assert "Traceback" not in cikti.out and "Traceback" not in cikti.err
