import os
import re
import datetime
import gspread
from time import sleep
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from fake_useragent import UserAgent
from oauth2client.service_account import ServiceAccountCredentials
from webdriver_manager.chrome import ChromeDriverManager

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
def get_ja_data(ws, SPREADSHEET_ID):
    scope = ['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/drive']
    credentials = ServiceAccountCredentials.from_json_keyfile_name('spreadsheet.json', scope)
    gc = gspread.authorize(credentials)
    sheet = gc.open_by_key(SPREADSHEET_ID).worksheet(ws)

    ja_data = sheet.get_all_values()
    ja_data.pop(0)
    return ja_data

def translate_data(ja_data):
    url = "https://www.deepl.com/ja/translator#en/ja/"
    ua = UserAgent()
    logger.debug(f'create_issue: UserAgent: {ua.chrome}')

    options = Options()
    options.add_argument(f'user-agent={ua.chrome}')

    chrome_service = fs.Service(executable_path=ChromeDriverManager().install())
    driver = webdriver.Chrome(service=chrome_service, options=options)

    driver.get(url)
    driver.maximize_window()

    for element in ja_data:
        try:
            driver.get(f'{url}{element[1]}')
            sleep(5)
            html = driver.page_source
            soup = BeautifulSoup(html, 'html.parser')
            text = soup.find(id="target-dummydiv").getText()
            yield text
        except Exception as err:
            logger.error(f'Error: {err}')
            yield "Err"

def write_response(response, ws, SPREADSHEET_ID):
    scope = ['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/drive']
    credentials = ServiceAccountCredentials.from_json_keyfile_name('spreadsheet.json', scope)
    gc = gspread.authorize(credentials)
    sheet = gc.open_by_key(SPREADSHEET_ID).worksheet(ws)

    cell_list = sheet.range(f'C2:C{len(response) + 1}')
    for i, cell in enumerate(cell_list):
            cell.value = response[i]
    sheet.update_cells(cell_list, value_input_option='USER_ENTERED')

### main_script ###
if __name__ == '__main__':
    SPREADSHEET_ID = "1lckHkBZPvCpuy8ex3rgchb0vm1evm-6xDecNLYuipdg"
    ws1 = "1"

    try:
        logger.debug("start_translation")
        ja_data = get_ja_data(ws1, SPREADSHEET_ID)
        response = list(translate_data(ja_data))
        write_response(response, ws1, SPREADSHEET_ID)
        exit(0)
    except Exception as err:
        logger.debug(f'Err: {err}')
        exit(1)
