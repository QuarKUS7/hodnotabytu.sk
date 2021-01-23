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
    kurenie: str= ''
    energ_cert: str= ''
    uzit_plocha: float=0
    cena_m2: float=0
    cena: float=0
    rok_vystavby: int=0
    pocet_podlazi: int=0
    pocet_izieb: int=0
    podlazie: int=0
    timestamp: int=0
    latitude: int=0
    longitude: int=0
    pocet_nadz_podlazi: int=0
    verejne_parkovanie: str= ''
    vytah: str= ''
    lodiza: str= ''
    balkon: str= ''
    garazove_stanie: str= ''
    garaz: str= ''
