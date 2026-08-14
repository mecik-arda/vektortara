from __future__ import annotations

import dataclasses
import enum
import uuid


class Ciddiyet(str, enum.Enum):
    KRITIK = "KRİTİK"
    YUKSEK = "YÜKSEK"
    ORTA = "ORTA"
    DUSUK = "DÜŞÜK"
    BILGI = "BİLGİ"

    @property
    def agirlik(self) -> int:
        return {
            Ciddiyet.KRITIK: 5,
            Ciddiyet.YUKSEK: 4,
            Ciddiyet.ORTA: 3,
            Ciddiyet.DUSUK: 2,
            Ciddiyet.BILGI: 1,
        }[self]


@dataclasses.dataclass
class Bulgu:
    ciddiyet: Ciddiyet
    baslik: str
    detay: str
    oneri: str
    kontrol: str
    veritabani: str
    kanit: str = ""
    kimlik: str = dataclasses.field(default_factory=lambda: str(uuid.uuid4()))

    def as_dict(self) -> dict:
        return {
            "ciddiyet": self.ciddiyet.value,
            "baslik": self.baslik,
            "detay": self.detay,
            "oneri": self.oneri,
            "kontrol": self.kontrol,
            "veritabani": self.veritabani,
            "kanit": self.kanit,
        }
