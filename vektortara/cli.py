from __future__ import annotations

import argparse
import json
import sys
from collections import Counter

from rich.console import Console
from rich.table import Table

from vektortara import __surum__, cve_vt, hedef
from vektortara.modeller import Ciddiyet
from vektortara.vtler.base import TaramaHatasi
from vektortara.vtler.chroma import ChromaTarayici
from vektortara.vtler.qdrant import QdrantTarayici
from vektortara.vtler.weaviate import WeaviateTarayici

TARAYICILAR = {
    "chroma": ChromaTarayici,
    "qdrant": QdrantTarayici,
    "weaviate": WeaviateTarayici,
}

RENKLER = {
    Ciddiyet.KRITIK: "bold red",
    Ciddiyet.YUKSEK: "red",
    Ciddiyet.ORTA: "yellow",
    Ciddiyet.DUSUK: "blue",
    Ciddiyet.BILGI: "dim",
}


def _ayristirici_kur() -> argparse.ArgumentParser:
    ayr = argparse.ArgumentParser(
        prog="vektortara",
        description="Vektör veritabanları için hafif, zarar vermeyen güvenlik tarayıcısı.",
    )
    ayr.add_argument("--surum", action="version", version=f"vektortara {__surum__}")
    alt = ayr.add_subparsers(dest="komut", required=True)

    tara = alt.add_parser("tara", help="Bir vektör veritabanı örneğini tara")
    tara.add_argument("hedef", help="Hedef sunucu (ör. localhost:8000, https://db.example.com)")
    tara.add_argument(
        "--tur",
        choices=["otomatik", "chroma", "qdrant", "weaviate"],
        default="otomatik",
        help="Veritabanı türü; belirtilmezse otomatik tespit edilir",
    )
    tara.add_argument("--port", type=int, help="Port belirtilmezse türün varsayılan portu kullanılır")
    tara.add_argument(
        "--derin",
        action="store_true",
        help="Yazma probu dahil derin denetim (koleksiyon oluşturur ve hemen siler)",
    )
    tara.add_argument("--json", action="store_true", help="Çıktıyı makine okunur JSON olarak bas")
    tara.add_argument("--zaman-asimi", type=float, default=5.0, help="İstek zaman aşımı (saniye)")
    tara.add_argument("--guvensiz-tls", action="store_true", help="TLS sertifika doğrulamasını atla")
    tara.set_defaults(islev=_tara)

    cve = alt.add_parser("cve", help="Bilinen CVE kayıtlarını listele")
    cve.add_argument(
        "veritabani",
        nargs="?",
        choices=["chromadb", "qdrant", "weaviate"],
        help="Filtre: chromadb | qdrant | weaviate",
    )
    cve.set_defaults(islev=_cve_listele)

    return ayr


def _tara(ayar: argparse.Namespace) -> int:
    console = Console(soft_wrap=True)
    try:
        temel_hedef = hedef.hedef_olustur(ayar.hedef, ayar.port)
    except hedef.HedefHatasi as hata:
        Console(stderr=True).print(f"[bold red]Hata:[/] {hata}")
        return 2
    port_verildi = ayar.port is not None or hedef.port_belli_mi(temel_hedef)

    if ayar.tur != "otomatik":
        sonuc = _tek_tara(TARAYICILAR[ayar.tur], temel_hedef, ayar)
        if sonuc is None:
            return 2
        return _sonuc_bas(TARAYICILAR[ayar.tur], temel_hedef, sonuc, ayar)

    adaylar: list[tuple[type, str]] = []
    if port_verildi:
        for sinif in TARAYICILAR.values():
            adaylar.append((sinif, temel_hedef))
    else:
        for sinif in TARAYICILAR.values():
            adaylar.append((sinif, hedef.hedef_olustur(ayar.hedef, sinif.varsayilan_port)))

    for sinif, aday_hedef in adaylar:
        sonuc = _tek_tara(sinif, aday_hedef, ayar, sadece_tespit=True)
        if sonuc is not None:
            return _sonuc_bas(sinif, aday_hedef, sonuc, ayar)

    console.print("[bold red]Hata:[/] Hedefte tanınan bir vektör veritabanı bulunamadı.")
    console.print(
        "İpucu: Türü elle belirtin — `vektortara tara <hedef> --tur chroma|qdrant|weaviate`"
    )
    return 2


def _tek_tara(
    sinif: type,
    hedef_url: str,
    ayar: argparse.Namespace,
    *,
    sadece_tespit: bool = False,
) -> list | None:
    try:
        tarayici = sinif(
            hedef_url,
            zaman_asimi=ayar.zaman_asimi,
            guvensiz_tls=ayar.guvensiz_tls,
            derin=ayar.derin,
        )
        try:
            if sadece_tespit and not tarayici.parmak_izi():
                return None
            return tarayici.tara()
        finally:
            tarayici.kapat()
    except TaramaHatasi as hata:
        if not sadece_tespit:
            Console(stderr=True).print(f"[bold red]Hata:[/] {hata}")
        return None
    except Exception:
        if sadece_tespit:
            return None
        raise


def _sonuc_bas(sinif: type, hedef_url: str, bulgular: list, ayar: argparse.Namespace) -> int:
    if ayar.json:
        cikti = {
            "hedef": hedef_url,
            "veritabani": sinif.veritabani_adi,
            "tls_dogrulamasi": not ayar.guvensiz_tls,
            "derin_mod": ayar.derin,
            "bulgu_sayisi": len(bulgular),
            "bulgular": [bulgu.as_dict() for bulgu in bulgular],
        }
        print(json.dumps(cikti, ensure_ascii=False, indent=2))
    else:
        _insan_okunur_bas(sinif.veritabani_adi, hedef_url, bulgular, ayar)
    return 1 if any(b.ciddiyet != Ciddiyet.BILGI for b in bulgular) else 0


def _insan_okunur_bas(
    veritabani: str,
    hedef_url: str,
    bulgular: list,
    ayar: argparse.Namespace,
) -> None:
    console = Console(soft_wrap=True)
    console.print()
    console.print(
        f"[bold]vektortara[/] — hedef: [bold cyan]{hedef_url}[/] · tür: [bold cyan]{veritabani}[/]"
    )
    if ayar.guvensiz_tls:
        console.print("[yellow]Uyarı: TLS sertifika doğrulaması kapalı (--guvensiz-tls).[/]")
    console.print()

    sayac = Counter(b.ciddiyet for b in bulgular)
    ozet = Table(show_header=False, box=None, padding=(0, 1))
    ozet.add_column(style="bold")
    ozet.add_column()
    for ciddiyet in (Ciddiyet.KRITIK, Ciddiyet.YUKSEK, Ciddiyet.ORTA, Ciddiyet.DUSUK, Ciddiyet.BILGI):
        ozet.add_row(f"[{RENKLER[ciddiyet]}]{ciddiyet.value}[/]", str(sayac.get(ciddiyet, 0)))
    console.print(ozet)
    console.print()

    for bulgu in sorted(bulgular, key=lambda b: b.ciddiyet.agirlik, reverse=True):
        console.print(f"[{RENKLER[bulgu.ciddiyet]}]{bulgu.ciddiyet.value}[/] [bold]{bulgu.baslik}[/]")
        console.print(f"  Detay: {bulgu.detay}")
        if bulgu.kanit:
            console.print(f"  Kanıt: [dim]{bulgu.kanit}[/]")
        console.print(f"  Öneri: {bulgu.oneri}")
        console.print()

    if not bulgular:
        console.print("[green]Herhangi bir bulgu yok — hedef temiz görünüyor.[/]")


def _cve_listele(ayar: argparse.Namespace) -> int:
    console = Console(soft_wrap=True)
    kayitlar = cve_vt.cve_kayitlarini_oku(ayar.veritabani)
    if not kayitlar:
        console.print("[yellow]Bu veritabanı için kayıt bulunamadı.[/]")
        return 0
    tablo = Table(title="Bilinen CVE Kayıtları", show_lines=True)
    tablo.add_column("ID", style="bold cyan")
    tablo.add_column("Ad")
    tablo.add_column("CVSS", justify="center")
    tablo.add_column("Etkilenen")
    tablo.add_column("Özet")
    for kayit in kayitlar:
        tablo.add_row(kayit.id, kayit.ad, kayit.cvss, kayit.etkilenen, kayit.ozet)
        tablo.add_row("", "", "", "", "Kaynaklar: " + " · ".join(kayit.kaynaklar))
    console.print(tablo)
    return 0


def _akis_utf8_yap() -> None:
    for akis in (sys.stdout, sys.stderr):
        try:
            akis.reconfigure(encoding="utf-8")
        except (AttributeError, OSError, ValueError):
            pass


def main(argv: list[str] | None = None) -> None:
    _akis_utf8_yap()
    ayr = _ayristirici_kur()
    ayar = ayr.parse_args(argv)
    try:
        kod = ayar.islev(ayar)
    except KeyboardInterrupt:
        sys.exit(130)
    except Exception as hata:
        Console(stderr=True).print(f"[bold red]Beklenmeyen hata:[/] {hata}")
        sys.exit(2)
    sys.exit(kod)


if __name__ == "__main__":
    main()
