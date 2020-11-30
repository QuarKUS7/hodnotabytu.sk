import re
import time
import json
import random
import requests
import pandas as pd
import unicodedata

from bs4 import BeautifulSoup

# url template
url = 'https://www.nehnutelnosti.sk/bratislava/byty/predaj/?p[page]='

SLEEP_TIME = 3


# Example inzerat
inzerat = {
    'Ulica':'',
    'Mesto':'',
    'Okres':'',
    'Druh':'',
    'Stav': '',
    'Uzit_plocha':0,
    'Cena_m2':0.0,
    'Cena':0,
    'ID':'',
    'Rok_vystavby':1900,
    'Pocet_podlazi':0,
    'Pocet_izieb':0,
    'Ener_cert': '',
    'Podlazie':0,
    'Vytah':False,
    'Kurenie':False,
    'Verejne_parkovanie':False,
}

def strip_accents(text):

    try:
        text = unicode(text, 'utf-8')
    except NameError: # unicode is a default on python 3
        pass

    text = unicodedata.normalize('NFD', text)\
           .encode('ascii', 'ignore')\
           .decode("utf-8")

    return str(text)


class Scraper:
    def __init__(self, url, page_parser, inzerat_parser):
        self.url = url
        self.page_parser = page_parser
        self.inzerat_parser = inzerat_parser

    def scrape(self):
        "Main function responsible for running scraper"
        output = []
        pager = 1
        while True:
            page = Page(url+str(pager))
            page.body = self.page_parser.process_page(page.url)
            page.inzeraty_url.extend(self.page_parser.get_inzerat_href(page.body))
            if page.inzeraty_url:
                pager+1
            else:
                break
            print(page.inzeraty_url)
            output.extend(self.inzerat_parser.process_all_inzerat_on_page(page.inzeraty_url))
            ##########
            break
            ##########
        return output


class Page:
    def __init__(self, url):
        self.url = url
        self.body = None
        self.inzeraty_url = []


class PageParser:
    def get_raw_page(self, page):
        "Get and parse page into bs4 object"
        time.sleep(random.uniform(1,5))
        response = requests.get(page)
        return response

    def parse_body_by_bs4(self, response):
        soup = BeautifulSoup(response.text, "html.parser")
        return soup

    def process_page(self, url):
        response = self.get_raw_page(url)
        soup = self.parse_body_by_bs4(response)
        return soup

    def get_inzerat_href(self, soup):
        "Find links to each inzerat in page. Usually there 30 inzerats on single page"
        inzeraty = soup.find_all('a', href=re.compile('\.sk/(\d){7}'))
        inzeraty = [inzerat['href'] for inzerat in inzeraty]
        inzeraty = list(set(inzeraty))
        return inzeraty

class InzeratParser:
    def parse_inzerat_html(self, url):
        "Parse page into bs4 object"
        time.sleep(random.uniform(1,5))
        response= requests.get(url)
        soup = BeautifulSoup(response.text, "html.parser")
        return soup

    def process_all_inzerat_on_page(self, inzeraty):
        records = []
        for i in inzeraty:
            print(i)
            soup = self.parse_inzerat_html(i)
            inzerat_info = self.get_info_from_inzerat(soup)
            record = self.create_inzerat_record(inzerat_info)
            records.append(record)
        return records

    def get_info_from_inzerat(self, soup):
        head_div = soup.find('div', {'class': 'sub--head'})
        info_div = head_div.find('div', {'class': 'parameter--info'})
        divTag = info_div.findAll('div')
        inzerat_info = {}
        for t in divTag:
            k, v = str(t.get_text()).split(':')
            inzerat_info[k] = v
        location_div = head_div.find('span', {'class': 'top--info-location'})
        location_text = location_div.get_text().replace('\n', '').split(',')
        inzerat_info['Okres'] = location_text[-1].strip()
        inzerat_info['Mesto'] = location_text[-2].strip()

        try:
            inzerat_info['Ulica'] = location_text[-3].strip()
        except (KeyError, IndexError):
            pass

        cena_div = head_div.find('div', {'class': 'price--main paramNo0'})
        inzerat_info['Cena'] = cena_div.get_text().strip()
        addit_div = soup.find('div', {'class': 'parameters--extra mt-4 mb-5'})
        if addit_div:
            divTag = addit_div.find('div', {'id': 'additional-features-modal-button'})
            divTag = divTag.findAll('div')
            for t in divTag:
                try:
                    k, v = str(t.get_text()).replace('\n','').split(':')
                except ValueError:
                    print(t)
                inzerat_info[k] = v.strip()

        gps_div = soup.find('div', {'id': 'map-detail'}).attrs['data-gps-marker']

        gps_info = json.loads(gps_div)
        inzerat_info['lat'] = gps_info['gpsLatitude']
        inzerat_info['lon'] = gps_info['gpsLongitude']
        return inzerat_info

    def get_mandatory_str_info(self, inzerat_info):

        inzerat = {}
        inzerat['ID'] = 'nehnutelnosti.sk_' + inzerat_info['ID inzerátu'].strip()
        inzerat['Mesto'] = inzerat_info['Mesto'].strip()
        inzerat['Okres'] = inzerat_info['Okres'].strip()
        inzerat['Druh'] = inzerat_info['Druh'].strip()
        try:
            inzerat['Stav'] = inzerat_info['Stav'].strip()
        except KeyError:
            pass
        try:
            inzerat['Uzit_plocha'] =  float(re.sub('[^0-9]','', inzerat_info['Úžit. plocha'])[:-1])
            inzerat['Cena_m2'] =  float(inzerat['Cena'] / inzerat['Uzit_plocha'])
        except KeyError:
            pass
        inzerat['Latitude'] = inzerat_info['lat']
        inzerat['Longitude'] = inzerat_info['lon']

        try:
            inzerat['Cena'] =  int(re.sub('[^0-9]','', inzerat_info['Cena']))
        except ValueError:
            pass

        return inzerat

    def get_mandatory_int_info(self, inzerat_info):

        inzerat = {}
        try:
            inzerat['Stav'] = inzerat_info['Stav'].strip()
        except KeyError:
            pass
        try:
            inzerat['Uzit_plocha'] =  float(re.sub('[^0-9]','', inzerat_info['Úžit. plocha'])[:-1])
            inzerat['Cena_m2'] =  float(inzerat['Cena'] / inzerat['Uzit_plocha'])
        except KeyError:
            pass
        inzerat['Latitude'] = inzerat_info['lat']
        inzerat['Longitude'] = inzerat_info['lon']

        try:
            inzerat['Cena'] =  int(re.sub('[^0-9]','', inzerat_info['Cena']))
        except ValueError:
            pass

        return inzerat

    def get_integer_voluntary_info(self, inzerat_info):

        voluntary_int_info_keys = ['Rok výstavby', 'Podlažie', 'Počet nadzemných podlaží']

        voluntary_int_info_columns = ['Rok_vystavby', 'Podlazie', 'Pocet_nadzem_podlazi']

        voluntary_int_info = {}
        for key, column in zip(voluntary_int_info_keys, voluntary_int_info_columns):
            try:
                voluntary_int_info[column] = inzerat_info[key]
            except KeyError:
                pass
        return voluntary_int_info

    def get_string_voluntary_info(self, inzerat_info):

        voluntary_str_info_keys = ['Ulica', 'Balkón', 'Kúrenie', 'Výťah', 'Energetický certifikát', 'Lodžia', 'Garáž', 'Garážové státie']

        voluntary_str_info_columns = ['Ulica', 'Balkon', 'Kurenie', 'Vytah', 'Ener_cert', 'Lodzia', 'Garaz', 'Garazove_statie']

        voluntary_str_info = {}
        for key, column in zip(voluntary_str_info_keys, voluntary_str_info_columns):
            try:
                voluntary_str_info[column] = inzerat_info[key]
            except KeyError:
                pass
        return voluntary_str_info

    def create_inzerat_record(self, inzerat_info):

        man_int_info = self.get_mandatory_int_info(inzerat_info)
        man_str_info = self.get_mandatory_str_info(inzerat_info)
        volun_int_info = self.get_integer_voluntary_info(inzerat_info)
        volun_str_info = self.get_string_voluntary_info(inzerat_info)

        inzerat_info = {}
        inzerat_info.update(man_str_info)
        inzerat_info.update(volun_str_info)
        inzerat_info = {key:strip_accents(value) for key,value in inzerat_info.items() if isinstance(value, str)}
        inzerat_info.update(man_int_info)
        inzerat_info.update(volun_int_info)

        return inzerat_info



if __name__ == '__main__':
    page_parser = PageParser()
    inzerat_parser = InzeratParser()
    scraper = Scraper(url, page_parser, inzerat_parser)
    records = scraper.scrape()
    print(records)
    df = pd.DataFrame(records)
    name = 'nehntelnosti_' + str(int(time.time())) + '.csv'
    fullpath = '~/projekty/zakolko/' + name
    print(fullpath)
    df.to_csv(fullpath)
