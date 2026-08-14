import pytest

from vektortara import cve_vt


def test_cve_kayitlari_filtresiz():
    kayitlar = cve_vt.cve_kayitlarini_oku()
    assert any(k.id == "CVE-2026-45829" for k in kayitlar)


def test_cve_kayitlari_filtreli():
    kayitlar = cve_vt.cve_kayitlarini_oku("chromadb")
    assert kayitlar and all(k.id == "CVE-2026-45829" for k in kayitlar)


def test_cve_kayitlari_bilinmeyen_veritabani():
    assert cve_vt.cve_kayitlarini_oku("olmayan-vt") == []


@pytest.mark.parametrize(
    ("surum", "aralik", "beklenen"),
    [
        ("1.0.0", ">=1.0.0", True),
        ("1.5.8", ">=1.0.0", True),
        ("2.1.0", ">=1.0.0", True),
        ("0.5.20", ">=1.0.0", False),
        ("1.0.0", "*", True),
        ("1.2.3", ">=1.0.0,<1.5.0", True),
        ("1.5.0", ">=1.0.0,<1.5.0", False),
        ("1.0.0rc1", ">=1.0.0", False),
        ("1.0.0a1", "==1.0.0a1", True),
    ],
)
def test_surum_etkileniyor(surum, aralik, beklenen):
    assert cve_vt.surum_etkileniyor(surum, aralik) is beklenen


def test_surum_araligi_hatali_ise_value_error():
    with pytest.raises(ValueError):
        cve_vt.surum_etkileniyor("1.0.0", "nedir-bu")


def test_gecersiz_surum_value_error():
    with pytest.raises(ValueError):
        cve_vt.surum_etkileniyor("1.2.foo", ">=1.0.0")
