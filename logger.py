import logging

LOGFILE = '/var/log/scraper.log'

def init_logger():
    log = logging.getLogger()
    formatter = logging.Formatter('%(asctime)s %(levelname)s [%(filename)s:%(lineno)d] %(message)s')
    file_handler = logging.FileHandler(LOGFILE)
    file_handler.setFormatter(formatter)
    file_handler.setLevel(10)
    log.addHandler(file_handler)
    log.setLevel(10)

    return log
