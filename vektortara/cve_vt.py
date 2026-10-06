from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

import yaml
from packaging.version import InvalidVersion, Version

_VERI_DOSYASI = Path(__file__).parent / "veriler" / "cve.yaml"

_GEREKLI_ALANLAR = ("id", "ad", "cvss", "cwe", "etkilenen", "ozet", "oneri", "kaynaklar")


@dataclass(frozen=True)
class CveKaydi:
    id: str
    ad: str
    cvss: str
    cwe: str
    etkilenen: str
    ozet: str
    oneri: str
    kaynaklar: list[str]


class CveKayitHatasi(RuntimeError):
    pass


def cve_kayitlarini_oku(veritabani: str | None = None) -> list[CveKaydi]:
    try:
        with open(_VERI_DOSYASI, encoding="utf-8") as dosya:
            ham = yaml.safe_load(dosya)
    except OSError as hata:
        raise CveKayitHatasi(f"CVE kayıt dosyası okunamadı: {_VERI_DOSYASI}") from hata
    except yaml.YAMLError as hata:
        raise CveKayitHatasi(f"CVE kayıt dosyası ayrıştırılamadı: {hata}") from hata
    if not isinstance(ham, dict) or not isinstance(ham.get("veritabanlari"), list):
        raise CveKayitHatasi("CVE kayıt dosyası beklenen yapıda değil: 'veritabanlari' listesi yok")
    kayitlar: list[CveKaydi] = []
    for grup in ham["veritabanlari"]:
        if not isinstance(grup, dict) or not isinstance(grup.get("ad"), str):
            raise CveKayitHatasi("CVE kayıt dosyasında grup 'ad' alanı eksik veya hatalı")
        if veritabani and grup["ad"] != veritabani:
            continue
        if not isinstance(grup.get("kayitlar"), list):
            raise CveKayitHatasi(f"CVE kayıt dosyasında grup 'kayitlar' listesi hatalı: {grup['ad']}")
        for kayit in grup["kayitlar"]:
            kayitlar.append(_kayit_dogrula(kayit))
    return kayitlar


def _gecerli_kaynak_urlsi(deger: object) -> bool:
    if not isinstance(deger, str):
        return False
    parca = urlsplit(deger)
    return parca.scheme in ("http", "https") and bool(parca.hostname)


def _kayit_dogrula(kayit: object) -> CveKaydi:
    if not isinstance(kayit, dict):
        raise CveKayitHatasi("CVE kaydı sözlük (dict) olmalı")
    eksik = [alan for alan in _GEREKLI_ALANLAR if alan not in kayit]
    if eksik:
        raise CveKayitHatasi(f"CVE kaydında eksik alanlar: {', '.join(eksik)}")
    for alan in ("id", "ad", "cwe", "etkilenen", "ozet", "oneri"):
        if not isinstance(kayit[alan], str):
            raise CveKayitHatasi(f"CVE kaydında '{alan}' alanı metin olmalı: {kayit.get('id', '?')}")
    if isinstance(kayit["cvss"], bool) or not isinstance(kayit["cvss"], str | int | float):
        raise CveKayitHatasi(f"CVE kaydında 'cvss' alanı hatalı: {kayit.get('id', '?')}")
    if not isinstance(kayit["kaynaklar"], list) or not all(
        _gecerli_kaynak_urlsi(k) for k in kayit["kaynaklar"]
    ):
        raise CveKayitHatasi(f"CVE kaydının 'kaynaklar' alanı hatalı: {kayit.get('id', '?')}")
    try:
        surum_etkileniyor("1.0.0", str(kayit["etkilenen"]))
    except ValueError as hata:
        raise CveKayitHatasi(f"CVE kaydının sürüm aralığı hatalı: {kayit.get('id', '?')}") from hata
    return CveKaydi(
        id=str(kayit["id"]),
        ad=str(kayit["ad"]),
        cvss=str(kayit["cvss"]),
        cwe=str(kayit["cwe"]),
        etkilenen=str(kayit["etkilenen"]),
        ozet=str(kayit["ozet"]),
        oneri=str(kayit["oneri"]),
        kaynaklar=[str(k) for k in kayit["kaynaklar"]],
    )


def _surum_nesnesi(surum: str) -> Version:
    try:
        return Version(surum.strip())
    except InvalidVersion as hata:
        raise ValueError(f"Geçersiz sürüm biçimi: {surum!r}") from hata


def _karsilastir(gercek: Version, islec: str, hedef: Version) -> bool:
    if islec == ">=":
        return gercek >= hedef
    if islec == "<=":
        return gercek <= hedef
    if islec == ">":
        return gercek > hedef
    if islec == "<":
        return gercek < hedef
    return gercek == hedef


def surum_etkileniyor(surum: str, aralik: str) -> bool:
    if aralik.strip() == "*":
        return True
    gercek = _surum_nesnesi(surum)
    kosullar = [parca.strip() for parca in aralik.split(",") if parca.strip()]
    for kosul in kosullar:
        eslesme = re.match(r"^(>=|<=|>|<|==)?\s*(.+)$", kosul)
        if not eslesme:
            raise ValueError(f"Anlaşılamayan sürüm aralığı: {kosul}")
        islec = eslesme.group(1) or "=="
        hedef = _surum_nesnesi(eslesme.group(2))
        if not _karsilastir(gercek, islec, hedef):
            return False
    return True
