import os
import re
import pathlib        
import datetime
import requests
import gspread
from time import sleep
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome import service as fs
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
    sheet = gc.open_by_key(SPREADSHEET_ID).worksheet('MainDomain')

    domain_info = sheet.get_all_values()
    domain_info.pop(0)
    return domain_info

def http_request(domain_info):
    for element in domain_info:
        logger.debug(f'check_main_domain_status: {element[0]}: http://{element[1]}/')
        try:
            req = requests.get(f'http://{element[1]}/')
            html = BeautifulSoup(req.text, 'html.parser')
            title = html.find('title').get_text()
            logger.debug(f'check_main_domain_status: status: {req.status_code}: title: {title}')
            yield [element[0], element[1], req.status_code, title]
        except Exception as err:
            logger.error(f'Error: check_main_domain_status: http_request: {err}')
            yield [element[0], element[1], "Timeout", "-"]

def write_response(response):
    SPREADSHEET_ID = os.environ['SERVER123_SSID']
    scope = ['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/drive']
    credentials = ServiceAccountCredentials.from_json_keyfile_name('spreadsheet.json', scope)
    gc = gspread.authorize(credentials)
    sheet = gc.open_by_key(SPREADSHEET_ID).worksheet('MainDomain')

    now = datetime.datetime.now()
    sheet.update_acell('E1', now.strftime('%Y-%m-%d %H:%M'))
    cell_list = sheet.range('C2:D301')
    i = 0
    for cell in cell_list:
        if i % 2 == 0:
            cell.value = response[int(i / 2)][2]
        else:
            cell.value = response[int(i / 2)][3]
        i += 1
    sheet.update_cells(cell_list, value_input_option='USER_ENTERED')

def create_message(response):
    flag = False
    message = 'ご担当者さま\n\n'
    message += '現時点でダウンしているドメイン一覧です。\n\n'
    message += 'ご確認お願い致します。\n\n'
    message += 'サーバー番号 メインドメイン HTTPステータスコード 内容\n'
    for element in response:
        if element[2] == 200 and element[3] == 'ERROR':
            continue ;
        else:
            flag = True
            message += f'{element[0]} {element[1]} {element[2]} {element[3]}\n'
    if flag == True:
        return message
    else:
        return None

def button_click(driver, button_text):
    buttons = driver.find_elements(By.TAG_NAME, "button")

    for button in buttons:
        if button.text == button_text:
            button.click()
            break

def create_issue(message):
    url = "https://member.123server.jp/members/login/"
    login = os.environ['SERVER123_USER']
    password = os.environ['SERVER123_PASS']

    ua = UserAgent()
    logger.debug(f'create_issue: UserAgent: {ua.chrome}')

    options = Options()
    options.add_argument(f'user-agent={ua.chrome}')

    try:
        chrome_service = fs.Service(executable_path=ChromeDriverManager().install())
        driver = webdriver.Chrome(service=chrome_service, options=options)

        driver.get(url)
        driver.maximize_window()

        driver.find_element(By.ID, "MemberContractId").send_keys(login)
        driver.find_element(By.ID, "MemberPassword").send_keys(password)
        button_click(driver, "ログイン")

        logger.debug('create_issue: login')
        sleep(3)

        driver.find_element(By.CLASS_NAME, 'main-menu').find_elements(By.TAG_NAME, 'li')[6].click()
        sleep(2)
        driver.find_element(By.XPATH, '//a[@href="/tickets/open"]').click()

        now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
        driver.implicitly_wait(60)
        driver.find_element(By.ID, "TicketTicketTitle").send_keys(f'現時点でのメインドメインのダウン {now}')
        driver.find_element(By.ID, "TicketBody").send_keys(message)
        sleep(10)
        driver.find_element(By.XPATH, '//input[@type="submit"]').click()
        sleep(10)

        driver.close()
        driver.quit()
    except Exception as err:
        logger.debug(f'Error: create_issue: {err}')
        exit(1)

### main_script ###
if __name__ == '__main__':

    try:
        logger.debug("check_main_domain_status: start get_domain_info")
        domain_info = get_domain_info()
        logger.debug("check_main_domain_status: start http_request")
        response = list(http_request(domain_info))
        write_response(response)
        message = create_message(response)
        logger.debug(message)
        if not message == None:
            create_issue(message)
        exit(0)
    except Exception as err:
        logger.debug(f'check_main_domain_status: {err}')
        exit(1)
