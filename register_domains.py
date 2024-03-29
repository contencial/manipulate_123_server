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
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
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
def install_autossl(driver, index, domain_info, server_no):
    while int(domain_info[index][0]) == server_no:
        domain_name = domain_info[index][1]

        driver.implicitly_wait(10)
        dropdown = driver.find_element(By.ID, 'domain_lets')
        select = Select(dropdown)
        select.select_by_value(domain_name)
        sleep(2)
        driver.implicitly_wait(600)
        driver.find_element(By.CLASS_NAME, 'fa-lock')

        driver.find_element(By.ID, 'btn-lets-add').click()
        sleep(2)
        driver.implicitly_wait(600)
        driver.find_element(By.CLASS_NAME, 'toast-title')
        sleep(1)

        logger.debug(f'register_domain_to_server: No.{server_no}: {domain_name}: autossl installed')
        index += 1
        if index >= len(domain_info):
            break

    return index

def register_domain_to_server(driver, index, domain_info, server_no):
    while int(domain_info[index][0]) == server_no:
        domain_name = domain_info[index][1]

        driver.implicitly_wait(300)
        driver.find_element(By.ID, "btn_add_domain").click()
        sleep(3)

        driver.find_element(By.ID, 'newdomain').send_keys(domain_name)
        driver.find_element(By.ID, 'pathdomain').send_keys(Keys.BACKSPACE * len(domain_name))
        driver.find_element(By.ID, 'pathdomain').send_keys(f'public_html/{domain_name}')
        driver.find_element(By.XPATH, '//button[@onclick="saveNewDomain()"]').click()
        sleep(2)
        driver.implicitly_wait(600)
        driver.find_element(By.CLASS_NAME, 'toast-title')
        sleep(1)

        logger.debug(f'register_domain_to_server: No.{server_no}: {domain_name}: registered')
        index += 1
        if index >= len(domain_info):
            break

def button_click(driver, button_text):
    buttons = driver.find_elements(By.TAG_NAME, "button")

    for button in buttons:
        if button.text == button_text:
            button.click()
            break

def login_to_serverlist(driver, login, password):
    driver.find_element(By.ID, "MemberContractId").send_keys(login)
    driver.find_element(By.ID, "MemberPassword").send_keys(password)
    button_click(driver, "ログイン")

    logger.debug('register_domain_info: login')
    sleep(3)

    driver.find_element(By.XPATH, '//a[@href="/servers/"]').click()

    logger.debug('register_domain_info: go to server_list')
    sleep(3)

def register_domain_info(domain_info):
    url = "https://member.123server.jp/members/login/"
    login = os.environ['SERVER123_USER']
    password = os.environ['SERVER123_PASS']
    cwp_login = os.environ['CWP_USER']
    
    ua = UserAgent()
    logger.debug(f'register_domain_info: UserAgent: {ua.chrome}')

    options = Options()
    options.add_argument(f'user-agent={ua.chrome}')
    options.add_argument('--ignore-ssl-errors=yes')

    capabilities = DesiredCapabilities.CHROME.copy()
    capabilities['acceptInsecureCerts'] = True
    
    try:
        chrome_service = fs.Service(executable_path=ChromeDriverManager().install())
        driver = webdriver.Chrome(service=chrome_service, options=options, desired_capabilities=capabilities)
        
        driver.get(url)
        driver.maximize_window()

        login_to_serverlist(driver, login, password)

        info_size = len(domain_info)
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

            if re.search(r"login", driver.current_url) != None:
                login_to_serverlist(driver, login, password)
                if server_no <= 100:
                    driver.find_element(By.LINK_TEXT, str(1)).click()
                elif server_no > 100 and server_no <= 200:
                    driver.find_element(By.LINK_TEXT, str(2)).click()
                elif server_no > 200:
                    driver.find_element(By.LINK_TEXT, str(3)).click()

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
            driver.find_element(By.XPATH, '//a[@href="?module=domains"]').click()
            register_domain_to_server(driver, index, domain_info, server_no)

            driver.implicitly_wait(60)
            driver.find_element(By.XPATH, '//li[@class="searchmenu"][3]').click()
            sleep(2)
            driver.find_element(By.XPATH, '//a[@href="?module=letsencrypt"]').click()
            index = install_autossl(driver, index, domain_info, server_no)

            driver.close()
            driver.switch_to.window(driver.window_handles[0])
            
        driver.close()
        driver.quit()
    except Exception as err:
        logger.debug(f'Error: register_domain_info: {err}')
        exit(1)

def get_domain_info():
    SPREADSHEET_ID = os.environ['MANIPULATION_PARAM_SSID']
    scope = ['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/drive']
    credentials = ServiceAccountCredentials.from_json_keyfile_name('spreadsheet.json', scope)
    gc = gspread.authorize(credentials)
    sheet = gc.open_by_key(SPREADSHEET_ID).worksheet('RegisterInfo')

    domain_info = sheet.get_all_values()
    domain_info.pop(0)
    return domain_info

### main_script ###
if __name__ == '__main__':

    try:
        logger.debug("register_domain: start get_domain_info")
        domain_info = get_domain_info()
        logger.debug("register_domain: start register_domain_info")
        register_domain_info(domain_info)
        exit(0)
    except Exception as err:
        logger.debug(f'register_domain: {err}')
        exit(1)
