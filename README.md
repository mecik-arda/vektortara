# vektortara

Vektör veritabanları için hafif, **zarar vermeyen** güvenlik tarayıcısı.

ChromaDB, Qdrant ve Weaviate örneklerini; kimlik doğrulama, bilinen CVE'ler, sürüm
ifşası ve CORS yapılandırması açısından denetler. Çıktılar Türkçedir, CI'da
kullanılabilir (`--json`, çıkış kodları).

> **İlham:** CVE-2026-45829 (ChromaToast) — ChromaDB'de kimlik doğrulamasız uzak kod
> çalıştırma. RAG yığınının en alt katmanındaki bu tür açıkların ağda hızlıca
> fark edilmesi için yazıldı.

---

## Özellikler

- **Tür tespiti** — hedefte hangi veritabanının koştuğunu otomatik anlar
  (`--tur otomatik`, varsayılan)
- **CVE denetimi** — yerleşik kayıt defteriyle sürüm karşılaştırması
  (şu an CVE-2026-45829 / ChromaToast)
- **Yetki denetimi** — okuma uç noktalarının kimlik doğrulamasız açık olup olmadığını sınar
- **Derin mod** — ChromaDB'de kimlik doğrulamasız koleksiyon oluşturma probu:
  ChromaToast saldırısının ön koşulunu kanıtlar, prob koleksiyonunu hemen siler
- **CORS denetimi** — Origin başlığının serbestçe yansıtılıp yansıtılmadığını kontrol eder
- **Çıkış kodları** — bulgu varsa 1, temizse 0, hata olursa 2; pipeline'lara bağlanır
- **JSON çıktı** — `--json` ile makine okunur sonuç

## Kurulum

```bash
git clone https://github.com/mecik-arda/vektortara
cd vektortara
pip install .
```

## Kullanım

```bash
# Türü otomatik tespit et (port verilmezse türlerin varsayılan portları denenir)
vektortara tara localhost:8000

# Türü elle belirt
vektortara tara https://db.example.com:6333 --tur qdrant

# ChromaToast ön koşulunu doğrula (koleksiyon oluşturur ve hemen siler)
vektortara tara localhost:8000 --tur chroma --derin

# CI için JSON çıktı
vektortara tara localhost:8000 --json

# Bilinen CVE kayıtlarını listele
vektortara cve
vektortara cve chromadb
```

Örnek çıktı:

```
vektortara — hedef: http://localhost:8000 · tür: chromadb

  KRİTİK  1
  YÜKSEK  1
  ORTA    1
  DÜŞÜK   1
  BİLGİ   0

KRİTİK ChromaToast (CVE-2026-45829) — sürüm 1.5.8 etkileniyor
  Detay: CVSS 10.0, CWE-94. Kimlik doğrulaması öncesi kod enjeksiyonu. ...
  Kanıt: sürüm=1.5.8 aralık=>=1.0.0
  Öneri: Sunucuyu kimlik doğrulama katmanı arkasına alın ve dış ağa açmayın. ...

YÜKSEK Kimlik doğrulamasız okuma erişimi
  Detay: Kimlik doğrulama olmadan koleksiyon listesi ve şema bilgileri okunabiliyor. ...
  Kanıt: GET /api/v2/tenants/default_tenant/databases/default_database/collections → 200 OK
  Öneri: Sunucuyu kimlik doğrulama gerektiren ters vekil arkasına alın.
```

## Denetlenenler

| Kontrol | chromadb | qdrant | weaviate |
|---|---|---|---|
| Sürüm tespiti ve ifşa | ✓ | ✓ | ✓ |
| CVE kayıt defteri karşılaştırması | ✓ | — | — |
| Kimlik doğrulamasız okuma erişimi | ✓ | ✓ | ✓ |
| Kimlik doğrulamasız yazma probu (`--derin`) | ✓ | — | — |
| CORS yansıtma | ✓ | ✓ | ✓ |
| OIDC yapılandırma varlığı | — | — | ✓ |

## Güvenlik modeli

- Varsayılan tarama **yalnızca okur**; hiçbir şey oluşturmaz, değiştirmez, silmez.
- `--derin` tek istisnadır: ChromaDB'ye `vektortara_probe_*` adında bir koleksiyon
  oluşturur ve **aynı anda siler**. Kod çalıştırmaz, embedding yapılandırması
  enjekte etmez; yalnızca uç noktanın kimlik doğrulamasız isteği kabul ettiğini kanıtlar.
  Silme başarısız olursa YÜKSEK seviyede bulgu üretilir ve temizlik komutu gösterilir.
- Yönlendirmeler yalnızca **aynı ana bilgisayar** içinde izlenir; farklı bir sunucuya
  ya da HTTPS'ten HTTP'ye yönlendirme reddedilir. Yönlendirme sırasında POST GET'e
  düşerse yazma probu başarılı sayılmaz.
- HTTP hedeflerde hostname, tarama başlangıcında bir kez çözümlenir ve bağlantılar
  sabitlenen IP'ye yapılır (IPv4 öncelikli, Host başlığı korunur). IP literal hedefler
  olduğu gibi kullanılır. HTTPS hedeflerde TLS/SNI uyumluluğu için sabitleme yapılmaz.
- Kullanıcı adı/parola içeren hedef URL'ler reddedilir.
- 5xx, 429 ve diğer belirsiz yanıtlar "doğrulanamadı" (ORTA) olarak raporlanır;
  asla sessizce "temiz" sayılmaz.
- Tarayıcıyı **yalnızca kendi sistemlerinizde veya yazılı izniniz olan hedeflerde**
  çalıştırın.

## Çıkış kodları

| Kod | Anlam |
|---|---|
| 0 | BİLGİ dışında bulgu yok — hedef temiz |
| 1 | En az bir bulgu (DÜŞÜK ve üzeri) |
| 2 | Hedefe ulaşılamadı veya tanınmadı |

## Geliştirme

```bash
pip install -e ".[test]"
pytest
ruff check .
```

Yeni CVE kayıtları `vektortara/veriler/cve.yaml` dosyasına eklenir; sürüm aralıkları
`>=1.0.0` veya `>=1.0.0,<1.6.0` biçimindedir. Yeni veritabanı desteği için
`vektortara/vtler/` altına `TemelTarayici`'dan türeyen bir sınıf eklemek yeterli.

## Yol haritası

- [ ] ChromaToast için ağ tabanlı embedding-injection kanıtı (kontrollü, opsiyonel)
- [ ] Daha fazla CVE kaydı (ChromaDB, Qdrant, Weaviate geçmişi)
- [ ] Birden çok hedefi liste dosyasından tarama
- [ ] Milvus, pgvector desteği

## Lisans

[MIT](LICENSE) — [Arda Meçik](https://github.com/mecik-arda)

Bu proje, Türkçe yapay zeka güvenliği kaynak listesi
[awesome-ai-security-tr](https://github.com/fevziegeyurtsevenler/awesome-ai-security-tr)
ekosistemine katkı kapsamında geliştirilmiştir.

---

## Yazar

**[Arda Meçik](https://github.com/mecik-arda)** — siber güvenlik ve yapay zeka güvenliği
üzerine çalışan bir geliştirici.

- GitHub: [github.com/mecik-arda](https://github.com/mecik-arda)

Projeyi beğendiyseniz yıldızlamayı unutmayın — vektör veritabanı güvenliği üzerine
yeni tarayıcılar, CVE kayıtları ve Türkçe güvenlik yazıları için profili takip edebilirsiniz.
