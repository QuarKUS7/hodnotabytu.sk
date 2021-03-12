# Dataclass representing inzerat
from dataclasses import dataclass, field


@dataclass
class Inzerat:
    ulica: str = ''
    mesto: str = ''
    okres: str= ''
    druh: str= ''
    stav: str= ''
    id: str= ''
    zdroj: str=''
    kurenie: str= ''
    energ_cert: str= ''
    orientacia: str= ''
    telkoint: str= ''
    uzit_plocha: float=-1
    cena_m2: float=-1
    cena: float=-1
    rok_vystavby: int=-1
    pocet_izieb: int=-1
    podlazie: int=-1
    timestamp: int=-1
    latitude: int=-1
    longitude: int=-1
    pocet_nadz_podlazi: int=-1
    verejne_parkovanie: str= ''
    vytah: str= ''
    lodzia: str= ''
    balkon: str= ''
    garazove_statie: str= ''
    garaz: str= ''
