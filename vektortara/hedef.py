from __future__ import annotations

import ipaddress
from urllib.parse import urlsplit, urlunsplit


class HedefHatasi(ValueError):
    pass


def hedef_olustur(hedef: str, port: int | None = None) -> str:
    if port is not None and not (1 <= port <= 65535):
        raise HedefHatasi(f"Geçersiz port: {port}")
    if "://" not in hedef:
        hedef = f"http://[{hedef}]" if hedef.count(":") > 1 and not hedef.startswith("[") else f"http://{hedef}"
    try:
        parca = urlsplit(hedef)
        url_portu = parca.port
    except ValueError as hata:
        raise HedefHatasi(f"Geçersiz hedef: {hedef!r}") from hata
    if not parca.hostname:
        raise HedefHatasi(f"Hedeften ana bilgisayar adı çıkarılamadı: {hedef!r}")
    if parca.username or parca.password or "@" in parca.hostname:
        raise HedefHatasi(
            "Hedef URL'de kullanıcı adı/parola bulunamaz; kimlik bilgileri çıktıya "
            "sızabileceği için reddedildi."
        )
    if parca.query:
        raise HedefHatasi(
            "Hedef URL sorgu parametresi içeremez; token benzeri değerlerin çıktıya "
            "sızma riski nedeniyle reddedildi."
        )
    if parca.scheme.lower() not in ("http", "https"):
        raise HedefHatasi(f"Desteklenmeyen şema: {parca.scheme}")
    konak = parca.hostname
    if ":" in konak:
        try:
            ipaddress.ip_address(konak)
        except ValueError as hata:
            raise HedefHatasi(f"Geçersiz ana bilgisayar adı: {konak!r}") from hata
    netloc = f"[{konak}]" if ":" in konak else konak
    son_port = url_portu if url_portu is not None else port
    if son_port is not None:
        netloc = f"{netloc}:{son_port}"
    return urlunsplit((parca.scheme, netloc, parca.path, parca.query, "")).rstrip("/")


def port_belli_mi(hedef: str) -> bool:
    if "://" not in hedef:
        hedef = f"http://[{hedef}]" if hedef.count(":") > 1 and not hedef.startswith("[") else f"http://{hedef}"
    return urlsplit(hedef).port is not None
