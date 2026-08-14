from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urljoin, urlsplit, urlunsplit

import httpx

import vektortara.modeller as modeller


class TaramaHatasi(Exception):
    pass


_DNS_ONBELLEK: dict[tuple[str, int], list] = {}


class TemelTarayici:
    veritabani_adi = "bilinmiyor"
    varsayilan_port = 8000

    _KOTU_KAYNAK = "https://kotu-ornek.example"

    def __init__(
        self,
        hedef: str,
        *,
        zaman_asimi: float = 5.0,
        guvensiz_tls: bool = False,
        derin: bool = False,
        transport: httpx.BaseTransport | None = None,
        konak_sabitle: bool = True,
    ):
        self.derin = derin
        self.guvensiz_tls = guvensiz_tls
        basliklar = {"User-Agent": "vektortara"}
        parca = urlsplit(hedef.rstrip("/"))
        self._ozgun_konak = parca.hostname
        netloc = parca.netloc
        self.hedef = urlunsplit((parca.scheme, netloc, parca.path, "", "")).rstrip("/")
        sabit = self._konak_sabitle(self.hedef) if konak_sabitle else None
        if sabit:
            self.hedef, basliklar["Host"] = sabit
        self._istemci = httpx.Client(
            timeout=zaman_asimi,
            verify=not guvensiz_tls,
            follow_redirects=False,
            headers=basliklar,
            transport=transport,
        )
        self._bulgular: list[modeller.Bulgu] = []

    @staticmethod
    def _dns_coz(konak: str, aile: int) -> list:
        anahtar = (konak, aile)
        if anahtar in _DNS_ONBELLEK:
            return _DNS_ONBELLEK[anahtar]
        try:
            sonuclar = socket.getaddrinfo(konak, None, aile, socket.SOCK_STREAM)
        except OSError:
            sonuclar = []
        _DNS_ONBELLEK[anahtar] = sonuclar
        return sonuclar

    @staticmethod
    def _konak_sabitle(hedef: str) -> tuple[str, str] | None:
        parca = urlsplit(hedef)
        konak = parca.hostname
        if not konak:
            return None
        try:
            ipaddress.ip_address(konak)
            return None
        except ValueError:
            pass
        if parca.scheme.lower() != "http":
            return None
        sonuclar: list = []
        for aile in (socket.AF_INET, socket.AF_INET6):
            sonuclar = TemelTarayici._dns_coz(konak, aile)
            if sonuclar:
                break
        if not sonuclar:
            return None
        ip_adresi = sonuclar[0][4][0]
        netloc = f"[{ip_adresi}]" if ":" in ip_adresi else ip_adresi
        if parca.port is not None:
            netloc = f"{netloc}:{parca.port}"
        sabit_hedef = urlunsplit((parca.scheme, netloc, parca.path, "", ""))
        host_basligi = f"{konak}:{parca.port}" if parca.port is not None else konak
        return sabit_hedef, host_basligi

    @staticmethod
    def durum_sinifi(kod: int) -> str:
        if 200 <= kod < 300:
            return "basarili"
        if kod in (401, 403):
            return "yetki_reddi"
        if kod == 429:
            return "hiz_siniri"
        if 300 <= kod < 400:
            return "yonlendirme"
        if 500 <= kod < 600:
            return "sunucu_hatasi"
        return "diger"

    def istek(
        self,
        yontem: str,
        yol: str,
        *,
        basliklar: dict[str, str] | None = None,
        govde: dict | None = None,
        yonlendirme: int = 3,
    ) -> httpx.Response:
        yonlendirme = max(0, yonlendirme)
        tam_url = self.hedef + yol
        self._yontem_degisti = False
        for _ in range(yonlendirme + 1):
            yanit = self._istemci.request(yontem, tam_url, headers=basliklar, json=govde)
            if yanit.status_code not in (301, 302, 303, 307, 308):
                return yanit
            konum = yanit.headers.get("location")
            if not konum:
                return yanit
            yeni_url = self._guvenli_yonlendirme(tam_url, konum)
            if yeni_url is None:
                return yanit
            if yanit.status_code in (301, 302, 303) and yontem != "GET":
                yontem, govde = "GET", None
                self._yontem_degisti = True
            tam_url = yeni_url
        return yanit

    @property
    def yontem_degisti(self) -> bool:
        return getattr(self, "_yontem_degisti", False)

    def _guvenli_yonlendirme(self, tam_url: str, konum: str) -> str | None:
        try:
            yeni = urlsplit(urljoin(tam_url, konum))
            eski = urlsplit(tam_url)
            eski_port = eski.port
            yeni_port = yeni.port
        except ValueError:
            return None
        if yeni.username or yeni.password:
            return None
        izinli_konaklar = {eski.hostname}
        if self._ozgun_konak:
            izinli_konaklar.add(self._ozgun_konak)
        if yeni.hostname not in izinli_konaklar:
            return None
        eski_sema, yeni_sema = eski.scheme.lower(), yeni.scheme.lower()
        if eski_sema == "https" and yeni_sema != "https":
            return None
        if yeni_sema != eski_sema:
            if yeni_port != eski_port:
                return None
        else:
            eski_etkin = eski_port or (443 if eski_sema == "https" else 80)
            yeni_etkin = yeni_port or (443 if yeni_sema == "https" else 80)
            if eski_etkin != yeni_etkin:
                return None
        return urljoin(tam_url, konum)

    @staticmethod
    def kanit_uret(yontem: str, yol: str, yanit: httpx.Response) -> str:
        return f"{yontem} {yol} -> {yanit.status_code} {yanit.reason_phrase}"

    def bulgu(
        self,
        ciddiyet: modeller.Ciddiyet,
        baslik: str,
        detay: str,
        oneri: str,
        kontrol: str,
        kanit: str = "",
    ) -> None:
        self._bulgular.append(
            modeller.Bulgu(
                ciddiyet=ciddiyet,
                baslik=baslik,
                detay=detay,
                oneri=oneri,
                kontrol=kontrol,
                veritabani=self.veritabani_adi,
                kanit=kanit,
            )
        )

    def cors_denetle(self, yol: str, kontrol: str) -> None:
        try:
            yanit = self.istek(
                "OPTIONS",
                yol,
                basliklar={
                    "Origin": self._KOTU_KAYNAK,
                    "Access-Control-Request-Method": "GET",
                },
            )
        except httpx.HTTPError as hata:
            self.bulgu(
                modeller.Ciddiyet.ORTA,
                "CORS denetimi doğrulanamadı",
                f"OPTIONS isteği başarısız: {hata}",
                "Bağlantıyı kontrol edip taramayı tekrarlayın.",
                kontrol,
            )
            return
        izin = yanit.headers.get("access-control-allow-origin", "")
        if izin in ("*", self._KOTU_KAYNAK):
            self.bulgu(
                modeller.Ciddiyet.ORTA,
                "CORS yapılandırması aşırı serbest",
                f"Sunucu Origin başlığını {izin!r} ile yansıtıyor; herhangi bir web sayfası "
                "tarayıcı üzerinden API'ye istek gönderebilir.",
                "CORS izin listesini yalnızca güvenilen kaynaklarla sınırlayın.",
                kontrol,
                self.kanit_uret("OPTIONS", yol, yanit),
            )

    def ozel_ag_notu(self, kontrol: str) -> None:
        konak = urlsplit(self.hedef).hostname
        if not konak:
            return
        try:
            ozel = not ipaddress.ip_address(konak).is_global
        except ValueError:
            ozel = konak == "localhost" or konak.endswith(
                (".local", ".internal", ".lan", ".home", ".corp")
            )
        if not ozel:
            self.bulgu(
                modeller.Ciddiyet.BILGI,
                "Hedef genel internet üzerinde",
                "Hedef adresi özel ağ veya loopback aralığında değil. Tarama için yazılı "
                "yetkinizin olduğundan emin olun.",
                "Yetkisiz hedefleri taramayın.",
                kontrol,
            )

    def parmak_izi(self) -> bool:
        raise NotImplementedError

    def tara(self) -> list[modeller.Bulgu]:
        raise NotImplementedError

    def kapat(self) -> None:
        self._istemci.close()
