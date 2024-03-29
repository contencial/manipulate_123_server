import os
import re
import datetime
import gspread
from time import sleep
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.select import Select
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome import service as fs
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
def check_domain_index(domains, domain_name):
    index = 0
    for domain in domains:
        print(f'{index}: {domain.text}')
        if re.match(domain_name, domain.text):
            return index;
        index += 1
    return None

def remove_domain_from_server(driver, index, domain_info, server_no, title):
    driver.find_element(By.CLASS_NAME, "navbar-minimalize").click()
    sleep(1)

    while int(domain_info[index][0]) == server_no:
        domain_name = domain_info[index][1]

        dropdown = driver.find_element(By.NAME, "DataTables_Table_0_length")
        select = Select(dropdown)
        select.select_by_value('100')
        sleep(2)
        
        domains = driver.find_elements(By.CLASS_NAME, "sorting_1")
        deletes = driver.find_elements(By.XPATH, f'//button[@title="{title}"]')
        print(f'domains: {len(domains)}, deletes: {len(deletes)}')
        domain_index = check_domain_index(domains, domain_name)
        if domain_index == None:
            logger.debug(f'remove_domain_to_server: No.{server_no}: {domain_name}: Not found')
            index += 1
            continue

        deletes[domain_index].click()
        sleep(2)
        driver.find_element(By.ID, "btnyesdel").click()
        sleep(2)

        logger.debug(f'remove_domain_to_server: No.{server_no}: {domain_name}')
        index += 1
        if index >= len(domain_info):
            break

    return index

def button_click(driver, button_text):
    buttons = driver.find_elements(By.TAG_NAME, "button")

    for button in buttons:
        if button.text == button_text:
            button.click()
            break

def remove_domain_info(domain_info):
    url = "https://member.123server.jp/members/login/"
    login = os.environ['SERVER123_USER']
    password = os.environ['SERVER123_PASS']
    cwp_login = os.environ['CWP_USER']
    
    ua = UserAgent()
    logger.debug(f'remove_domain_info: UserAgent: {ua.chrome}')

    options = Options()
    options.add_argument(f'user-agent={ua.chrome}')
    options.add_argument('--ignore-ssl-errors=yes')
    options.add_argument('--ignore-certificate-errors')
    
    try:
        chrome_service = fs.Service(executable_path=ChromeDriverManager().install())
        driver = webdriver.Chrome(service=chrome_service, options=options)
        
        driver.get(url)
        driver.maximize_window()

        driver.find_element(By.ID, "MemberContractId").send_keys(login)
        driver.find_element(By.ID, "MemberPassword").send_keys(password)
        button_click(driver, "ログイン")
        
        logger.debug('remove_domain_info: login')
        sleep(3)
        
        driver.find_element(By.XPATH, '//a[@href="/servers/"]').click()
        
        logger.debug('remove_domain_info: go to server_list')
        sleep(3)

        info_size = len(domain_info)
        logger.debug(f'remove_domain_info: list_size: {info_size}')
        index = 0
        while index < info_size:
            server_no = int(domain_info[index][0])
            if server_no <= 100:
                driver.find_element(By.LINK_TEXT, str(1)).click()
            elif server_no > 100 and server_no <= 200:
                driver.find_element(By.LINK_TEXT, str(2)).click()
            elif server_no > 200:
                driver.find_element(By.LINK_TEXT, str(3)).click()
            sleep(3)

            login_button = driver.find_elements(By.XPATH, '//button[@type="submit"]')
            list_no = server_no % 100 - 1
            login_button[list_no].click()
            sleep(4)
            
            driver.switch_to.window(driver.window_handles[1])
            driver.implicitly_wait(200)
            driver.find_element(By.ID, "username").send_keys(cwp_login)
            driver.find_element(By.ID, "password").send_keys(password)
            driver.find_element(By.ID, "btnsubmit").click()
            driver.implicitly_wait(60)

            driver.find_element(By.XPATH, '//li[@class="searchmenu"][3]').click()
            sleep(2)
            domain_btn = driver.find_element(By.XPATH, '//a[@href="?module=domains"]')
            if re.search("Domain", domain_btn.text):
                title = "Delete"
            else:
                title = "削除する"
            domain_btn.click()
            sleep(7)

            index = remove_domain_from_server(driver, index, domain_info, server_no, title)
            driver.close()
            driver.switch_to.window(driver.window_handles[0])
            
        driver.close()
        driver.quit()
    except Exception as err:
        logger.debug(f'Error: remove_domain_info: {err}')
        exit(1)

def get_domain_info():
    SPREADSHEET_ID = os.environ['MANIPULATION_PARAM_SSID']
    scope = ['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/drive']
    credentials = ServiceAccountCredentials.from_json_keyfile_name('spreadsheet.json', scope)
    gc = gspread.authorize(credentials)
    sheet = gc.open_by_key(SPREADSHEET_ID).worksheet('RemoveInfo123')

    domain_info = sheet.get_all_values()
    domain_info.pop(0)
    return domain_info

### main_script ###
if __name__ == '__main__':

    try:
        logger.debug("remove_domain: start get_domain_info")
        domain_info = get_domain_info()
        if len(domain_info) == 0:
            logger.debug("remove_domain: no remove target")
            exit(0)
        logger.debug("remove_domain: start remove_domain_info")
        remove_domain_info(domain_info)
        exit(0)
    except Exception as err:
        logger.debug(f'remove_domain: {err}')
        exit(1)
