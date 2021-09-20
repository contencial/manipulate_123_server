import os
import re
import datetime
import gspread
import openpyxl
from time import sleep
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.select import Select
from fake_useragent import UserAgent
from oauth2client.service_account import ServiceAccountCredentials
from webdriver_manager.chrome import ChromeDriverManager

# Logger setting
from logging import getLogger, FileHandler, DEBUG
logger = getLogger(__name__)
today = datetime.datetime.now()
os.makedirs('./log', exist_ok=True)
handler = FileHandler(f'log/{today.strftime("%Y-%m-%d")}_result.log', mode='a')
handler.setLevel(DEBUG)
logger.setLevel(DEBUG)
logger.addHandler(handler)
logger.propagate = False

### functions ###
def download_template(downloadsDirPath):
    url = "https://123server.kijidaikousurunara.biz/"
    login = os.environ['SHINOBI_USER']
    password = os.environ['SHINOBI_PASS']
    
    ua = UserAgent()
    logger.debug(f'download_template: UserAgent: {ua.chrome}')

    options = Options()
    options.add_argument(f'user-agent={ua.chrome}')

    prefs = {
        "profile.default_content_settings.popups": 1,
        "download.default_directory":
                os.path.abspath(downloadsDirPath),
        "directory_upgrade": True
    }
    options.add_experimental_option("prefs", prefs)
    
    try:
        driver = webdriver.Chrome(ChromeDriverManager().install(), options=options)
        
        driver.get(url)
        driver.maximize_window()

        driver.find_element_by_xpath('//a[@href="https://kiji-daiko.biz-samurai.com/order/123server/transport"]').click()
        driver.implicitly_wait(10)
        driver.find_element_by_id('login').click()
        driver.implicitly_wait(10)
        driver.find_element_by_id('login_id').send_keys(login)
        driver.find_element_by_id('login_pass').send_keys(password)
        driver.find_element_by_id('registrationForm').submit()
        logger.debug('download_template: login')
        driver.implicitly_wait(10)
        
        driver.find_element_by_xpath('//a[@href="/order/upload-order"]').click()
        driver.implicitly_wait(10)
        driver.find_elements_by_class_name('col-xs-6')[1].find_element_by_xpath('//a[@href="/img/keyword_template.xlsx"]').click()

        return driver
    except Exception as err:
        logger.debug(f'Error: download_template: {err}')
        exit(1)

def check_keyword(kw):
    if kw == '口コミ':
        return '評価'
    else:
        return kw

def create_shinobi_order(fileName):
    SPREADSHEET_ID = os.environ['MEASUREMENT_SSID']
    scope = ['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/drive']
    credentials = ServiceAccountCredentials.from_json_keyfile_name('spreadsheet.json', scope)
    gc = gspread.authorize(credentials)
    sheet = gc.open_by_key(SPREADSHEET_ID).sheet1

    measurement_info = sheet.get_all_values()
    measurement_info.pop(0)
    measurement_info.pop(0)
    logger.debug("shinobi_order: get measurement data")

    wb = openpyxl.load_workbook(fileName)
    sheet = wb['キーワード指定']

    logger.debug("shinobi_order: start creating...")
    total = 0
    index = 4
    for element in measurement_info:
        if element[1] == '':
            break
        if element[1] == '0':
            continue
        genre = element[3]
        kw1 = check_keyword(element[5])
        kw2 = check_keyword(element[6])
        kw3 = check_keyword(element[7])
        kw4 = check_keyword(element[8])
        kw5 = check_keyword(element[9])
        kw6 = check_keyword(element[10])
        kw7 = check_keyword(element[11])
        kw8 = check_keyword(element[12])
        kw9 = check_keyword(element[13])
        kw10 = check_keyword(element[14])
        volume = element[1]

        sheet[f'B{index}'] = genre
        sheet[f'C{index}'] = kw1
        sheet[f'D{index}'] = kw2
        sheet[f'E{index}'] = kw3
        sheet[f'F{index}'] = kw4
        sheet[f'G{index}'] = kw5
        sheet[f'H{index}'] = kw6
        sheet[f'I{index}'] = kw7
        sheet[f'J{index}'] = kw8
        sheet[f'K{index}'] = kw9
        sheet[f'L{index}'] = kw10
        sheet[f'S{index}'] = int(volume)
        sheet[f'T{index}'] = 1500
        sheet[f'U{index}'] = '体験談'
        sheet[f'V{index}'] = '指定なし'

        total += int(volume)
        index += 1
        logger.debug(f"shinobi_order: created volume: {total}")

    wb.save(fileName)

### main_script ###
if __name__ == '__main__':

    try:
        downloadsDirPath = './excel'
        os.makedirs(downloadsDirPath, exist_ok=True)
        fileName = downloadsDirPath + '/keyword_template.xlsx'
        if os.path.exists(fileName):
            os.remove(fileName)

        logger.debug("shinobi_order: download keyword_template.xlsx")
        driver = download_template(downloadsDirPath)

        logger.debug("shinobi_order: create shinobi order")
        create_shinobi_order(fileName)
        exit(0)
    except Exception as err:
        logger.debug(f'shinobi_order: {err}')
        exit(1)
