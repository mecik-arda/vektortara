from __future__ import annotations

import json

import httpx

import vektortara.modeller as modeller
from vektortara.vtler.base import TaramaHatasi, TemelTarayici


class WeaviateTarayici(TemelTarayici):
    veritabani_adi = "weaviate"
    varsayilan_port = 8080

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._meta_yanit: httpx.Response | None = None

    def parmak_izi(self) -> bool:
        try:
            self._meta_yanit = self.istek("GET", "/v1/meta")
        except httpx.HTTPError:
            return False
        if self._meta_yanit.status_code != 200:
            return False
        try:
            veri = self._meta_yanit.json()
        except json.JSONDecodeError:
            return False
        return isinstance(veri, dict) and "version" in veri

    def tara(self) -> list[modeller.Bulgu]:
        try:
            if self._meta_yanit is None:
                self._meta_yanit = self.istek("GET", "/v1/meta")
        except httpx.ConnectError as hata:
            raise TaramaHatasi(f"Weaviate'a ulaşılamadı: {hata}") from hata
        if self._meta_yanit.status_code != 200:
            raise TaramaHatasi(
                f"Weaviate meta uç noktası beklenmedik yanıt verdi: {self._meta_yanit.status_code}"
            )
        self.ozel_ag_notu("weaviate-hedef")
        self._surum_kontrolu()
        self._anonim_erisim_kontrolu()
        self._oidc_kontrolu()
        self.cors_denetle("/v1/schema", "weaviate-cors")
        return self._bulgular

    def _surum_kontrolu(self) -> None:
        kanit = self.kanit_uret("GET", "/v1/meta", self._meta_yanit)
        try:
            veri = self._meta_yanit.json()
        except json.JSONDecodeError:
            self.bulgu(
                modeller.Ciddiyet.ORTA,
                "Sürüm denetimi doğrulanamadı",
                "Meta uç noktası geçerli JSON döndürmedi; sürüm bilgisi doğrulanamadı.",
                "Sunucu yanıtını elle inceleyin.",
                "weaviate-surum",
                kanit,
            )
            return
        if not isinstance(veri, dict):
            self.bulgu(
                modeller.Ciddiyet.ORTA,
                "Sürüm denetimi doğrulanamadı",
                "Meta yanıtı beklenen sözlük yapısında değil; sürüm bilgisi doğrulanamadı.",
                "Sunucu yanıtını elle inceleyin.",
                "weaviate-surum",
                kanit,
            )
            return
        surum = veri.get("version")
        if surum:
            self.bulgu(
                modeller.Ciddiyet.DUSUK,
                "Sürüm bilgisi kimlik doğrulamasız okunabiliyor",
                f"Sunucu, sürüm bilgisini ({surum}) meta uç noktasından paylaşıyor.",
                "Meta uç noktasını ters vekil üzerinde kapatın.",
                "weaviate-surum",
                kanit,
            )

    def _anonim_erisim_kontrolu(self) -> None:
        yol = "/v1/schema"
        try:
            yanit = self.istek("GET", yol)
        except httpx.HTTPError as hata:
            self.bulgu(
                modeller.Ciddiyet.ORTA,
                "Anonim erişim doğrulanamadı",
                f"Şema isteği başarısız: {hata}",
                "Bağlantıyı kontrol edip taramayı tekrarlayın.",
                "weaviate-yetki",
            )
            return
        kanit = self.kanit_uret("GET", yol, yanit)
        durum = self.durum_sinifi(yanit.status_code)
        if durum == "basarili":
            self.bulgu(
                modeller.Ciddiyet.YUKSEK,
                "Anonim erişim etkin",
                "Kimlik doğrulama olmadan tüm şema (sınıflar ve özellikler) okunabiliyor. "
                "Weaviate varsayılan yapılandırmasında anonim erişim açıktır.",
                "AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED=false yapın ve API anahtarı ya da "
                "OIDC zorunlu kılın.",
                "weaviate-yetki",
                kanit,
            )
        elif durum == "yetki_reddi":
            self.bulgu(
                modeller.Ciddiyet.BILGI,
                "Kimlik doğrulama zorunlu",
                "Şema uç noktası kimlik doğrulama istiyor; anonim okuma kapalı.",
                "Ek işlem gerekmiyor.",
                "weaviate-yetki",
                kanit,
            )
        else:
            self.bulgu(
                modeller.Ciddiyet.ORTA,
                "Anonim erişim doğrulanamadı",
                f"Şema uç noktası beklenmedik yanıt verdi ({yanit.status_code}); "
                "kimlik doğrulama durumu kesinleştirilemedi.",
                "Sunucu yanıt verdiğinde taramayı tekrarlayın.",
                "weaviate-yetki",
                kanit,
            )

    def _oidc_kontrolu(self) -> None:
        yol = "/v1/.well-known/openid-configuration"
        try:
            yanit = self.istek("GET", yol)
        except httpx.HTTPError as hata:
            self.bulgu(
                modeller.Ciddiyet.ORTA,
                "OIDC denetimi doğrulanamadı",
                f"OpenID Connect keşif isteği başarısız: {hata}",
                "Bağlantıyı kontrol edip taramayı tekrarlayın.",
                "weaviate-oidc",
            )
            return
        kanit = self.kanit_uret("GET", yol, yanit)
        if yanit.status_code == 200:
            try:
                gecerli = isinstance(yanit.json(), dict)
            except json.JSONDecodeError:
                gecerli = False
            if gecerli:
                self.bulgu(
                    modeller.Ciddiyet.BILGI,
                    "OIDC yapılandırılmış",
                    "OpenID Connect keşif belgesi mevcut; kimlik doğrulama katmanı tanımlı.",
                    "Anonim erişimin ayrıca kapalı olduğundan emin olun.",
                    "weaviate-oidc",
                    kanit,
                )
            else:
                self.bulgu(
                    modeller.Ciddiyet.ORTA,
                    "OIDC denetimi doğrulanamadı",
                    "OpenID Connect keşif uç noktası beklenen sözlük yapısında yanıt "
                    "döndürmedi.",
                    "Sunucu yanıtını elle inceleyin.",
                    "weaviate-oidc",
                    kanit,
                )
        elif yanit.status_code == 404:
            self.bulgu(
                modeller.Ciddiyet.ORTA,
                "OIDC yapılandırılmamış",
                "OpenID Connect keşif belgesi bulunamadı; kimlik doğrulama katmanı "
                "yalnızca varsayılan ayarlara bağlı.",
                "Kurumsal dağıtımlarda OIDC veya API anahtarı kimlik doğrulamasını zorunlu "
                "tutun.",
                "weaviate-oidc",
                kanit,
            )
        else:
            self.bulgu(
                modeller.Ciddiyet.ORTA,
                "OIDC denetimi doğrulanamadı",
                f"OpenID Connect keşif uç noktası beklenmedik yanıt verdi "
                f"({yanit.status_code}).",
                "Sunucu yanıt verdiğinde taramayı tekrarlayın.",
                "weaviate-oidc",
                kanit,
            )
