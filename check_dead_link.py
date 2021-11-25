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

def check_dead_link(domain_info):
    url = "https://www.dead-link-checker.com/ja/"
    ua = UserAgent()
    logger.debug(f'create_issue: UserAgent: {ua.chrome}')

    options = Options()
    options.add_argument(f'user-agent={ua.chrome}')

    driver = webdriver.Chrome(ChromeDriverManager().install(), options=options)

    driver.get(url)
    driver.maximize_window()

    for element in domain_info:
        logger.debug(f'check_dead_link: {element[0]}: http://{element[5]}/')
        if element[6] == "FALSE" or element[7] == "FALSE" or element[8] == "FALSE":
            logger.debug(f'check_dead_link: status: existance status is False/')
            yield [element[0], element[5], "-"]
            continue
        try:
            target = f"https://www.{element[5]}"
            driver.get(url)
            driver.find_element_by_id("starturl").send_keys(Keys.BACKSPACE * len("http://"))
            driver.find_element_by_id("starturl").send_keys(target)
            driver.find_element_by_id("btn_submit").click()

            wait = WebDriverWait(driver, 60)
            text = "終了しました"
            wait.until(expected_conditions.text_to_be_present_in_element((By.ID, "short_msg"), text))

            cnt_err = driver.find_element_by_id("ct_err").text
            logger.debug(f'check_dead_link: err: {cnt_err}')
            yield [element[0], element[5], cnt_err]
        except Exception as err:
            logger.error(f'Error: check_dead_link: check_dead_link: {err}')
            yield [element[0], element[5], "Err"]

def write_response(response):
    SPREADSHEET_ID = os.environ['SERVER123_SSID']
    scope = ['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/drive']
    credentials = ServiceAccountCredentials.from_json_keyfile_name('spreadsheet.json', scope)
    gc = gspread.authorize(credentials)
    sheet = gc.open_by_key(SPREADSHEET_ID).worksheet('Main')

    now = datetime.datetime.now()
    sheet.update_acell('S1', now.strftime('%m/%d %H:%M'))
    cell_list = sheet.range(f'S3:S{len(response) + 2}')
    for i, cell in enumerate(cell_list):
            cell.value = response[i][2]
    sheet.update_cells(cell_list, value_input_option='USER_ENTERED')

### main_script ###
if __name__ == '__main__':

    try:
        logger.debug("check_dead_link: start get_domain_info")
        domain_info = get_domain_info()
        logger.debug("check_dead_link: start http_request")
        response = list(check_dead_link(domain_info))
        write_response(response)
        logger.debug(message)
        exit(0)
    except Exception as err:
        logger.debug(f'check_dead_link: {err}')
        exit(1)
