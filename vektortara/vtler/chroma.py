from __future__ import annotations

import json
import random
import string

import httpx

import vektortara.cve_vt as cve_vt
import vektortara.modeller as modeller
from vektortara.vtler.base import TaramaHatasi, TemelTarayici

_TENANT = "default_tenant"
_VERITABANI = "default_database"
_TASLAK_KOLEKSIYON = "vektortara_probe_"


class ChromaTarayici(TemelTarayici):
    veritabani_adi = "chromadb"
    varsayilan_port = 8000

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._api_secimi: str | None = None

    def _api_sec(self) -> str:
        if self._api_secimi:
            return self._api_secimi
        for yol in ("/api/v2/heartbeat", "/api/v1/heartbeat"):
            try:
                yanit = self.istek("GET", yol)
            except httpx.ConnectError:
                raise
            except httpx.HTTPError:
                continue
            if yanit.status_code != 200:
                continue
            try:
                veri = yanit.json()
            except json.JSONDecodeError:
                continue
            if isinstance(veri, dict) and any("heartbeat" in anahtar for anahtar in veri):
                self._api_secimi = "v2" if yol.startswith("/api/v2") else "v1"
                return self._api_secimi
        raise TaramaHatasi("ChromaDB heartbeat alınamadı; hedef bir ChromaDB örneği olmayabilir.")

    def _kalp_yolu(self) -> str:
        return f"/api/{self._api_sec()}/heartbeat"

    def _koleksiyon_yolu(self) -> str:
        if self._api_sec() == "v2":
            return f"/api/v2/tenants/{_TENANT}/databases/{_VERITABANI}/collections"
        return "/api/v1/collections"

    def parmak_izi(self) -> bool:
        try:
            self._api_sec()
        except (TaramaHatasi, httpx.HTTPError):
            return False
        return True

    def tara(self) -> list[modeller.Bulgu]:
        try:
            self._api_sec()
        except httpx.ConnectError as hata:
            raise TaramaHatasi(f"ChromaDB'ye ulaşılamadı: {hata}") from hata
        self.ozel_ag_notu("chroma-hedef")
        surum, surum_kaniti = self._surum_bilgisi()
        self._surum_kontrolu(surum, surum_kaniti)
        self._cve_kontrolu(surum)
        self._yetki_kontrolu()
        self.cors_denetle(self._kalp_yolu(), "chroma-cors")
        if self.derin:
            self._yazma_probu()
        return self._bulgular

    def _surum_bilgisi(self) -> tuple[str | None, str]:
        yol = f"/api/{self._api_sec()}/version"
        try:
            yanit = self.istek("GET", yol)
        except httpx.ConnectError:
            raise
        except httpx.HTTPError:
            return None, ""
        if yanit.status_code != 200:
            return None, self.kanit_uret("GET", yol, yanit)
        kanit = self.kanit_uret("GET", yol, yanit)
        try:
            veri = yanit.json()
        except json.JSONDecodeError:
            return None, kanit
        if isinstance(veri, dict) and isinstance(veri.get("version"), str):
            return veri["version"], kanit
        if isinstance(veri, str):
            return veri.strip().strip('"'), kanit
        return None, kanit

    def _surum_kontrolu(self, surum: str | None, kanit: str) -> None:
        if surum:
            self.bulgu(
                modeller.Ciddiyet.DUSUK,
                "Sürüm bilgisi kimlik doğrulamasız okunabiliyor",
                f"Sunucu, sürüm bilgisini ({surum}) kimlik doğrulama istemeden paylaşıyor. "
                "Saldırgan bu bilgiyle sürüme özel istismar seçebilir.",
                "Sürüm uç noktasını ters vekil üzerinde kapatın veya erişimi kısıtlayın.",
                "chroma-surum",
                kanit,
            )

    def _cve_kontrolu(self, surum: str | None) -> None:
        kayitlar = cve_vt.cve_kayitlarini_oku(self.veritabani_adi)
        if surum is None:
            self.bulgu(
                modeller.Ciddiyet.BILGI,
                "Sürüm okunamadı, CVE denetimi yapılamadı",
                "Sunucu yanıt veriyor ancak sürüm bilgisi alınamadı. Bilinen CVE'lerin "
                "sürüm aralığına denk düşüp düşmediği doğrulanamıyor.",
                "Sürümü elle öğrenip `vektortara cve chromadb` ile karşılaştırın.",
                "chroma-cve",
            )
            return
        for kayit in kayitlar:
            try:
                etkilendi = cve_vt.surum_etkileniyor(surum, kayit.etkilenen)
            except ValueError:
                self.bulgu(
                    modeller.Ciddiyet.BILGI,
                    f"{kayit.id} için sürüm ayrıştırılamadı",
                    f"Sunucunun bildirdiği sürüm ({surum!r}) beklenen biçimde değil; "
                    "CVE etki denetimi yapılamadı.",
                    "Sürümü elle doğrulayın.",
                    "chroma-cve",
                )
                continue
            if etkilendi:
                self.bulgu(
                    modeller.Ciddiyet.KRITIK,
                    f"{kayit.ad} ({kayit.id}) — sürüm {surum} etkileniyor",
                    f"CVSS {kayit.cvss}, {kayit.cwe}. {kayit.ozet}",
                    kayit.oneri,
                    "chroma-cve",
                    f"sürüm={surum} aralık={kayit.etkilenen}",
                )
            else:
                self.bulgu(
                    modeller.Ciddiyet.BILGI,
                    f"{kayit.id} için sürüm {surum} etkilenmiyor",
                    f"Tespit edilen sürüm ({surum}), etkilenen aralığın "
                    f"({kayit.etkilenen}) dışında.",
                    "Ek işlem gerekmiyor.",
                    "chroma-cve",
                )

    def _yetki_kontrolu(self) -> None:
        yol = self._koleksiyon_yolu()
        try:
            yanit = self.istek("GET", yol)
        except httpx.HTTPError as hata:
            self.bulgu(
                modeller.Ciddiyet.ORTA,
                "Okuma erişimi doğrulanamadı",
                f"Koleksiyon listesi isteği başarısız: {hata}",
                "Bağlantıyı kontrol edip taramayı tekrarlayın.",
                "chroma-yetki",
            )
            return
        kanit = self.kanit_uret("GET", yol, yanit)
        durum = self.durum_sinifi(yanit.status_code)
        if durum == "basarili":
            self.bulgu(
                modeller.Ciddiyet.YUKSEK,
                "Kimlik doğrulamasız okuma erişimi",
                "Kimlik doğrulama olmadan koleksiyon listesi ve şema bilgileri okunabiliyor. "
                "Açıkta kalan bir ChromaDB, RAG bilgi tabanınızın tamamını sızdırır.",
                "Sunucuyu kimlik doğrulama gerektiren ters vekil arkasına alın.",
                "chroma-yetki",
                kanit,
            )
        elif durum == "yetki_reddi":
            self.bulgu(
                modeller.Ciddiyet.BILGI,
                "Kimlik doğrulama zorunlu",
                "Koleksiyon uç noktası kimlik doğrulama istiyor; okuma erişimi kapalı.",
                "Ek işlem gerekmiyor.",
                "chroma-yetki",
                kanit,
            )
        else:
            self.bulgu(
                modeller.Ciddiyet.ORTA,
                "Okuma erişimi doğrulanamadı",
                f"Koleksiyon listesi beklenmedik yanıt verdi ({yanit.status_code}); "
                "kimlik doğrulama durumu kesinleştirilemedi.",
                "Uç noktanın kimlik doğrulamasız erişime kapalı olduğunu elle doğrulayın.",
                "chroma-yetki",
                kanit,
            )

    def _yazma_probu(self) -> None:
        ad = _TASLAK_KOLEKSIYON + "".join(random.choices(string.ascii_lowercase, k=8))
        yol = self._koleksiyon_yolu()
        govdeler = (
            {"name": ad},
            {"name": ad, "configuration": {"name": "default"}},
        )
        olustu = False
        olusturma_kaniti = ""
        try:
            for govde in govdeler:
                try:
                    yanit = self.istek("POST", yol, govde=govde)
                except httpx.HTTPError as hata:
                    self.bulgu(
                        modeller.Ciddiyet.ORTA,
                        "Yazma probu doğrulanamadı",
                        f"Koleksiyon oluşturma isteği başarısız: {hata}",
                        "Bağlantıyı kontrol edip derin taramayı tekrarlayın.",
                        "chroma-yazma",
                    )
                    return
                durum = self.durum_sinifi(yanit.status_code)
                kanit = self.kanit_uret("POST", yol, yanit)
                if durum == "basarili" and self.yontem_degisti:
                    self.bulgu(
                        modeller.Ciddiyet.ORTA,
                        "Yazma probu doğrulanamadı",
                        "Koleksiyon oluşturma isteği yönlendirme sırasında GET'e dönüştü; "
                        "kimlik doğrulamasız yazma erişimi kanıtlanamadı.",
                        "Uç noktayı elle doğrulayın veya yönlendirme olmayan bir adresle "
                        "derin taramayı tekrarlayın.",
                        "chroma-yazma",
                        kanit,
                    )
                    return
                if durum == "basarili":
                    olustu = True
                    olusturma_kaniti = f"POST {yol} -> {yanit.status_code} (probe koleksiyonu: {ad})"
                    self.bulgu(
                        modeller.Ciddiyet.KRITIK,
                        "Kimlik doğrulamasız yazma erişimi — ChromaToast ön koşulu doğrulandı",
                        "Kimlik doğrulama olmadan koleksiyon oluşturulabildi. CVE-2026-45829 "
                        "saldırısı tam olarak bu uç noktadan embedding işlevi enjeksiyonuyla "
                        "uzak kod çalıştırıyor.",
                        "Sunucuyu derhal izole edin, kimlik doğrulama katmanı ekleyin ve yama "
                        "durumunu HiddenLayer raporundan kontrol edin.",
                        "chroma-yazma",
                        olusturma_kaniti,
                    )
                    break
                if durum == "yetki_reddi":
                    self.bulgu(
                        modeller.Ciddiyet.BILGI,
                        "Yazma erişimi kimlik doğrulama istiyor",
                        "Koleksiyon oluşturma uç noktası kimlik doğrulamasız isteği reddetti.",
                        "Ek işlem gerekmiyor.",
                        "chroma-yazma",
                        kanit,
                    )
                    return
                if durum in ("sunucu_hatasi", "hiz_siniri", "yonlendirme"):
                    self.bulgu(
                        modeller.Ciddiyet.ORTA,
                        "Yazma probu doğrulanamadı",
                        f"Sunucu koleksiyon oluşturma isteğine {yanit.status_code} döndürdü; "
                        "kimlik doğrulamasız yazma erişimi ne doğrulanabildi ne elendi.",
                        "Sunucu yanıt verdiğinde derin taramayı tekrarlayın.",
                        "chroma-yazma",
                        kanit,
                    )
                    return
            if not olustu:
                self.bulgu(
                    modeller.Ciddiyet.BILGI,
                    "Yazma probu sonuçsuz",
                    "Koleksiyon oluşturma istekleri başarılı olmadı; yazma erişimi varsa bile "
                    "doğrulanamadı.",
                    "Uç noktanın kimlik doğrulamasız erişime kapalı olduğunu elle doğrulayın.",
                    "chroma-yazma",
                )
        finally:
            if olustu:
                self._probu_temizle(ad)

    def _probu_temizle(self, ad: str) -> None:
        yol = f"{self._koleksiyon_yolu()}/{ad}"
        try:
            yanit = self.istek("DELETE", yol)
        except httpx.HTTPError as hata:
            self._temizleme_hatasi(ad, yol, f"istek başarısız: {hata}")
            return
        kanit = f"DELETE {yol} -> {yanit.status_code} {yanit.reason_phrase}"
        if self.yontem_degisti:
            self._temizleme_hatasi(
                ad,
                yol,
                f"{kanit} ; yönlendirme yöntemi GET'e düşürdü, silme doğrulanamadı",
            )
            return
        if self.durum_sinifi(yanit.status_code) == "basarili" or yanit.status_code == 404:
            self._temizlik_kaniti_ekle(kanit)
        else:
            self._temizleme_hatasi(ad, yol, kanit)

    def _temizlik_kaniti_ekle(self, kanit: str) -> None:
        for bulgu in reversed(self._bulgular):
            if bulgu.kontrol == "chroma-yazma" and bulgu.ciddiyet == modeller.Ciddiyet.KRITIK:
                bulgu.kanit = f"{bulgu.kanit} ; temizlik: {kanit}"
                return

    def _temizleme_hatasi(self, ad: str, yol: str, kanit: str) -> None:
        self.bulgu(
            modeller.Ciddiyet.YUKSEK,
            "Probe koleksiyonu silinemedi",
            f"Derin taramanın oluşturduğu {ad!r} koleksiyonu hedefte kaldı. "
            f"Elle temizleyin: DELETE {yol}",
            "Yukarıdaki isteği elle gönderip koleksiyonu silin.",
            "chroma-yazma",
            kanit,
        )
