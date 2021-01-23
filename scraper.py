import os
import re
import sys
import time
import json
import logging
import random
import requests
import pandas as pd
import unicodedata

from bs4 import BeautifulSoup
from datetime import datetime

from inzerat import Inzerat

LOGFILE = '/var/log/scraper.log'

SLEEP_TIME = 3

# url template
url = 'https://www.nehnutelnosti.sk/bratislava/byty/predaj/?p[page]='

def strip_accents(text):

    try:
        text = unicode(text, 'utf-8')
    except NameError: # unicode is a default on python 3
        pass

    text = unicodedata.normalize('NFD', text)\
           .encode('ascii', 'ignore')\
           .decode("utf-8")

    return str(text)

def init_logger():
    log = logging.getLogger()
    formatter = logging.Formatter('%(asctime)s %(levelname)s [%(filename)s:%(lineno)d] %(message)s')
    file_handler = logging.FileHandler(LOGFILE)
    file_handler.setFormatter(formatter)
    file_handler.setLevel(10)
    log.addHandler(file_handler)
    log.setLevel(10)

    return log

def make_request(url):
    "Make request and get response"
    time.sleep(random.uniform(1,5))
    response = requests.get(url, timeout=60)
    return response

def parse_response(response):
    return BeautifulSoup(response.text, "html.parser")


class Scraper:

    def __init__(self, url, inzerat_parser):
        self.url = url
        self.inzerat_parser = inzerat_parser

    def scrape(self):
        "Main function responsible for running scraper"
        output = []
        pager = 1
        while True:
            page = Page(url+str(pager))

            log.info(page.url)

            page.process_page()

            # scraper reached last page
            if not page.inzeraty_url:
                return output

            log.info(page.inzeraty_url)

            processed = self.inzerat_parser.get_all_inzeraty_on_page(page.inzeraty_url)

            if not processed:
                log.info('No more new inzeraty!')
                return output

            output.extend(processed)
            pager += 1

        return output


class Page:

    def __init__(self, url):
        self.url = url
        self.inzeraty_url = []
        self.body = None

    def process_page(self):
        response = make_request(self.url)
        self.body = parse_response(response)
        self.get_inzerat_href()

    def get_inzerat_href(self):
        "Find links to each inzerat in page. Usually there 30 inzerats on single page"
        inzeraty = self.body.find_all('a', href=re.compile('\.sk/(\d){7}'))
        inzeraty = [inzerat['href'] for inzerat in inzeraty]
        self.inzeraty_url = list(set(inzeraty))


class InzeratParser:

    def __init__(self, base):
        self.base = base

    def parse_inzerat(self, url):
        response = make_request(url)
        body = parse_response(response)
        return body

    def has_already_seen(self, i):
        inzerat_id = 'nehnutelnosti.sk_' + i.split('/')[3]
        return inzerat_id in self.base.ID.values

    def process_inzerat(self, i):
        try:
            body = self.parse_inzerat(i)
        except TimeoutError:
            log.error('Timeout pre: {}'.format(i))

        try:
            inzerat_info = self.get_info_from_inzerat(body)
        except AttributeError:
            log.error(i)
            return []
        return inzerat_info

    def get_all_inzeraty_on_page(self, inzeraty_url):
        inzeraty = []
        for inzerat_url in inzeraty_url:
            if self.has_already_seen(inzerat_url):
                continue

            inzerat_info = self.process_inzerat(inzerat_url)

            if not inzerat_info:
                continue

            inzerat = self.create_inzerat_record(inzerat_info)

            inzeraty.append(inzerat)

        return inzeraty

    def get_info_from_inzerat(self, body):
        head_div = body.find('div', {'class': 'sub--head'})
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
        addit_div = body.find('div', {'class': 'parameters--extra mt-4 mb-5'})
        if addit_div:
            divTag = addit_div.find('div', {'id': 'additional-features-modal-button'})
            divTag = divTag.findAll('div')
            for t in divTag:
                try:
                    k, v = str(t.get_text()).replace('\n','').split(':')
                except ValueError:
                    log.error(t)
                    continue
                inzerat_info[k] = v.strip()

        gps_div = body.find('div', {'id': 'map-detail'}).attrs['data-gps-marker']

        gps_info = json.loads(gps_div)
        inzerat_info['lat'] = gps_info['gpsLatitude']
        inzerat_info['lon'] = gps_info['gpsLongitude']
        for key, value in inzerat_info.items():
            if isinstance(value, str):
                inzerat_info[key] = strip_accents(value)
        return inzerat_info

    def get_str_info(self, inzerat_info, inzerat):
        inzerat.id = 'nehnutelnosti.sk_' + inzerat_info['ID inzerátu'].strip()
        inzerat.mesto = inzerat_info['Mesto'].strip()
        inzerat.okres = inzerat_info['Okres'].strip()
        inzerat.druh = inzerat_info['Druh'].strip()
        try:
            inzerat.stav = inzerat_info['Stav'].strip()
        except KeyError:
            pass
        voluntary_str_info_keys = ['Ulica', 'Balkón', 'Kúrenie', 'Výťah', 'Energetický certifikát', 'Lodžia', 'Garáž', 'Garážové státie']
        voluntary_str_info_keys = ['Ulica', 'Balkon', 'Kurenie', 'Vytah', 'Energeticky certifikat', 'Lodzia', 'Garaz', 'Garazove statie']

        voluntary_str_info_columns = ['ulica', 'balkon', 'burenie', 'vytah', 'ener_cert', 'lodzia', 'garaz', 'garazove_statie']

        for key, column in zip(voluntary_str_info_keys, voluntary_str_info_columns):
            try:
                inzerat.column = inzerat_info[key]
            except KeyError:
                pass

    def get_int_info(self, inzerat_info, inzerat):
        try:
            inzerat.cena =  int(re.sub('[^0-9]','', inzerat_info['Cena']))
        except ValueError:
            pass

        try:
            inzerat.uzit_plocha = float(re.sub('[^0-9]','', inzerat_info['Úžit. plocha'])[:-1])
            inzerat.cena_m2 = float(inzerat.cena / inzerat.uzit_plocha)
        except KeyError:
            pass

        inzerat.latitude = inzerat_info['lat']
        inzerat.longitude = inzerat_info['lon']

        voluntary_int_info_keys = ['Rok výstavby', 'Podlažie', 'Počet nadzemných podlaží']
        voluntary_int_info_keys = ['Rok vystavby', 'Podlazie', 'Pocet nadzemnych podlazi']

        voluntary_int_info_columns = ['rok_vystavby', 'podlazie', 'pocet_nadz_podlazi']

        for key, column in zip(voluntary_int_info_keys, voluntary_int_info_columns):
            try:
                inzerat.column = inzerat_info[key]
            except KeyError:
                pass

    def create_inzerat_record(self, inzerat_info):

        inzerat = Inzerat()

        self.get_int_info(inzerat_info, inzerat)
        self.get_str_info(inzerat_info, inzerat)


        inzerat.timestamp = datetime.now().isoformat()

        return inzerat


if __name__ == '__main__':

    log = init_logger()

    log.info('Scraping started!')
    basepath = os.getcwd() + '/base.csv'
    base_df = pd.read_csv(basepath)

    inzerat_parser = InzeratParser(base_df)
    scraper = Scraper(url, inzerat_parser)
    records = scraper.scrape()

    if not records:
        log.info('No new inzeraty, quiting without output!')
        sys.exit()

    df = pd.DataFrame(records)
    df_new = pd.concat([base_df + df])

    name = '/nehnutelnosti_' + str(int(time.time())) + '.csv'

    FULLPATH = os.getcwd() + name
    log.info('Saving to {}'.format(FULLPATH))
    log.info('New inzeraty {}'.format(df.ID.values))
    log.info('Base len {}, new base len {}'.format(base_df.shape[0], df_new.shape[0]))

    df_new.to_csv(FULLPATH)
    log.info('Scraping done!')
