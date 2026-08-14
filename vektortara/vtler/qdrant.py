from __future__ import annotations

import json

import httpx

import vektortara.modeller as modeller
from vektortara.vtler.base import TaramaHatasi, TemelTarayici


class QdrantTarayici(TemelTarayici):
    veritabani_adi = "qdrant"
    varsayilan_port = 6333

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._kok_yanit: httpx.Response | None = None
        self._telemetri_yaniti: httpx.Response | None = None
        self._telemetri_hatasi: Exception | None = None

    def parmak_izi(self) -> bool:
        try:
            self._kok_yanit = self.istek("GET", "/")
        except httpx.HTTPError:
            return False
        if self._kok_yanit.status_code == 200 and "qdrant" in self._kok_yanit.text.lower():
            return True
        telemetri = self._telemetri_iste()
        if telemetri is not None and telemetri.status_code == 200:
            try:
                veri = telemetri.json()
            except json.JSONDecodeError:
                return False
            if isinstance(veri, dict):
                uygulama = veri.get("app")
                if isinstance(uygulama, dict) and str(uygulama.get("name", "")).startswith(
                    "qdrant"
                ):
                    return True
        return False

    def _telemetri_iste(self) -> httpx.Response | None:
        if self._telemetri_yaniti is None and self._telemetri_hatasi is None:
            try:
                self._telemetri_yaniti = self.istek("GET", "/telemetry")
            except httpx.HTTPError as hata:
                self._telemetri_hatasi = hata
        return self._telemetri_yaniti

    def tara(self) -> list[modeller.Bulgu]:
        try:
            if self._kok_yanit is None:
                self._kok_yanit = self.istek("GET", "/")
        except httpx.ConnectError as hata:
            raise TaramaHatasi(f"Qdrant'a ulaşılamadı: {hata}") from hata
        if self._kok_yanit.status_code != 200:
            raise TaramaHatasi(
                f"Qdrant kök uç noktası beklenmedik yanıt verdi: {self._kok_yanit.status_code}"
            )
        self.ozel_ag_notu("qdrant-hedef")
        self._surum_kontrolu()
        self._api_anahtari_kontrolu()
        self.cors_denetle("/collections", "qdrant-cors")
        return self._bulgular

    def _surum_kontrolu(self) -> None:
        telemetri = self._telemetri_iste()
        if telemetri is None:
            if self._telemetri_hatasi is not None:
                self.bulgu(
                    modeller.Ciddiyet.ORTA,
                    "Sürüm denetimi doğrulanamadı",
                    f"Telemetri isteği başarısız: {self._telemetri_hatasi}",
                    "Bağlantıyı kontrol edip taramayı tekrarlayın.",
                    "qdrant-surum",
                )
            return
        if telemetri.status_code != 200:
            self.bulgu(
                modeller.Ciddiyet.ORTA,
                "Sürüm denetimi doğrulanamadı",
                f"Telemetri uç noktası beklenmedik yanıt verdi ({telemetri.status_code}); "
                "sürüm bilgisi doğrulanamadı.",
                "Sunucu yanıt verdiğinde taramayı tekrarlayın.",
                "qdrant-surum",
                self.kanit_uret("GET", "/telemetry", telemetri),
            )
            return
        kanit = self.kanit_uret("GET", "/telemetry", telemetri)
        try:
            veri = telemetri.json()
        except json.JSONDecodeError:
            self.bulgu(
                modeller.Ciddiyet.ORTA,
                "Sürüm denetimi doğrulanamadı",
                "Telemetri uç noktası geçerli JSON döndürmedi; sürüm bilgisi "
                "doğrulanamadı.",
                "Sunucu yanıtını elle inceleyin.",
                "qdrant-surum",
                kanit,
            )
            return
        if not isinstance(veri, dict):
            self.bulgu(
                modeller.Ciddiyet.ORTA,
                "Sürüm denetimi doğrulanamadı",
                "Telemetri yanıtı beklenen sözlük yapısında değil; sürüm bilgisi "
                "doğrulanamadı.",
                "Sunucu yanıtını elle inceleyin.",
                "qdrant-surum",
                kanit,
            )
            return
        uygulama = veri.get("app")
        if not isinstance(uygulama, dict):
            self.bulgu(
                modeller.Ciddiyet.ORTA,
                "Sürüm denetimi doğrulanamadı",
                "Telemetri yanıtında 'app' alanı eksik veya hatalı; sürüm bilgisi "
                "doğrulanamadı.",
                "Sunucu yanıtını elle inceleyin.",
                "qdrant-surum",
                kanit,
            )
            return
        surum = uygulama.get("version")
        if surum:
            self.bulgu(
                modeller.Ciddiyet.DUSUK,
                "Sürüm bilgisi kimlik doğrulamasız okunabiliyor",
                f"Sunucu, sürüm bilgisini ({surum}) telemetri uç noktasından paylaşıyor.",
                "Telemetri uç noktasını ters vekil üzerinde kapatın.",
                "qdrant-surum",
                kanit,
            )

    def _api_anahtari_kontrolu(self) -> None:
        yol = "/collections"
        try:
            yanit = self.istek("GET", yol, basliklar={"api-key": "vektortara-gecersiz-anahtar"})
        except httpx.HTTPError as hata:
            self.bulgu(
                modeller.Ciddiyet.ORTA,
                "Kimlik doğrulama denetimi doğrulanamadı",
                f"Koleksiyon listesi isteği başarısız: {hata}",
                "Bağlantıyı kontrol edip taramayı tekrarlayın.",
                "qdrant-yetki",
            )
            return
        kanit = self.kanit_uret("GET", yol, yanit)
        durum = self.durum_sinifi(yanit.status_code)
        if durum == "basarili":
            self.bulgu(
                modeller.Ciddiyet.YUKSEK,
                "API anahtarı denetlenmiyor — kimlik doğrulama yok",
                "Geçersiz bir API anahtarıyla koleksiyon listesi alınabildi. Qdrant açık "
                "kaynak sürümünde kimlik doğrulama varsayılan olarak kapalıdır; yalnızca "
                "anahtar yapılandırılmışsa denetlenir.",
                "API anahtarını yapılandırın (Qdrant ≥ 1.9) veya sunucuyu kimlik doğrulamalı "
                "ters vekil arkasına alın.",
                "qdrant-yetki",
                kanit,
            )
        elif durum == "yetki_reddi":
            self.bulgu(
                modeller.Ciddiyet.BILGI,
                "API anahtarı denetleniyor",
                "Geçersiz anahtarla gelen istek reddedildi; kimlik doğrulama etkin.",
                "Ek işlem gerekmiyor.",
                "qdrant-yetki",
                kanit,
            )
        else:
            self.bulgu(
                modeller.Ciddiyet.ORTA,
                "Kimlik doğrulama denetimi doğrulanamadı",
                f"Koleksiyon listesi beklenmedik yanıt verdi ({yanit.status_code}); "
                "anahtar denetiminin etkin olup olmadığı kesinleştirilemedi.",
                "Sunucu yanıt verdiğinde taramayı tekrarlayın.",
                "qdrant-yetki",
                kanit,
            )
