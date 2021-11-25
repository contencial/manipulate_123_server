import os
import re
import datetime
import requests
import gspread
from time import sleep
from bs4 import BeautifulSoup
from oauth2client.service_account import ServiceAccountCredentials

# Logger setting
from logging import getLogger, FileHandler, DEBUG
logger = getLogger(__name__)
today = datetime.datetime.now()
handler = FileHandler(f'log/{today.strftime("%Y-%m-%d")}_result.log', mode='a')
handler.setLevel(DEBUG)
logger.setLevel(DEBUG)
logger.addHandler(handler)
logger.propagate = False

### functions ###
def get_domain_info():
    SPREADSHEET_ID = os.environ['SERVER123_SSID']
    scope = ['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/drive']
    credentials = ServiceAccountCredentials.from_json_keyfile_name('spreadsheet.json', scope)
    gc = gspread.authorize(credentials)
    sheet = gc.open_by_key(SPREADSHEET_ID).worksheet('Main')

    domain_info = sheet.get_all_values()
    domain_info.pop(0)
    domain_info.pop(0)
    return domain_info

def http_request(domain_info):
    for element in domain_info:
        logger.debug(f'check_http_status: {element[0]}: http://{element[5]}/')
        if element[6] == "FALSE" or element[7] == "FALSE" or element[8] == "FALSE":
            logger.debug(f'check_http_status: status: existance status is False/')
            yield [element[0], element[5], "-", "-"]
            continue
        try:
            req = requests.get(f'http://{element[5]}/')
            html = BeautifulSoup(req.text, 'html.parser')
            title = html.find('title').get_text()
            logger.debug(f'check_http_status: status: {req.status_code}: title: {title}')
            yield [element[0], element[5], req.status_code, title]
        except Exception as err:
            logger.error(f'Error: check_http_status: http_request: {err}')
            yield [element[0], element[5], "Timeout", "-"]

def write_response(response):
    SPREADSHEET_ID = os.environ['SERVER123_SSID']
    scope = ['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/drive']
    credentials = ServiceAccountCredentials.from_json_keyfile_name('spreadsheet.json', scope)
    gc = gspread.authorize(credentials)
    sheet = gc.open_by_key(SPREADSHEET_ID).worksheet('Main')

    now = datetime.datetime.now()
    sheet.update_acell('K1', now.strftime('%m/%d %H:%M'))
    cell_list = sheet.range(f'J3:K{len(response) + 2}')
    i = 0
    for cell in cell_list:
        if i % 2 == 0:
            cell.value = response[int(i / 2)][2]
        else:
            cell.value = response[int(i / 2)][3]
        i += 1
    sheet.update_cells(cell_list, value_input_option='USER_ENTERED')

### main_script ###
if __name__ == '__main__':

    try:
        logger.debug("check_http_status: start get_domain_info")
        domain_info = get_domain_info()
        logger.debug("check_http_status: start http_request")
        response = list(http_request(domain_info))
        write_response(response)
        exit(0)
    except Exception as err:
        logger.debug(f'check_http_status: {err}')
        exit(1)
