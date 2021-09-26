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
from fake_useragent import UserAgent
from oauth2client.service_account import ServiceAccountCredentials
from webdriver_manager.chrome import ChromeDriverManager

# Logger setting
from logging import getLogger, FileHandler, DEBUG
logger = getLogger(__name__)
os.makedirs('./log', exist_ok=True)
handler = FileHandler(f'log/autossl.log', mode='a')
handler.setLevel(DEBUG)
logger.setLevel(DEBUG)
logger.addHandler(handler)
logger.propagate = False

### functions ###
def write_autossl(driver, server_no):
    driver.implicitly_wait(10)
    dropdown = driver.find_element_by_name('ssl_table_length')
    select = Select(dropdown)
    select.select_by_value('100')
    sleep(2)
    ssl_list = driver.find_elements_by_class_name('sorting_1')
    for element in ssl_list:
        match = re.search(r'^[\w\-\.]+', element.text)
        logger.debug(f'{server_no} {match.group()}')
    
def button_click(driver, button_text):
    buttons = driver.find_elements_by_tag_name("button")

    for button in buttons:
        if button.text == button_text:
            button.click()
            break

def collect_autossl():
    url = "https://member.123server.jp/members/login/"
    login = os.environ['SERVER123_USER']
    password = os.environ['SERVER123_PASS']
    cwp_login = os.environ['CWP_USER']
    
    ua = UserAgent()
    logger.debug(f'collect_autossl: UserAgent: {ua.chrome}')

    options = Options()
    options.add_argument(f'user-agent={ua.chrome}')
    options.add_argument('--ignore-ssl-errors=yes')
    options.add_argument('--ignore-certificate-errors')
    
    try:
        driver = webdriver.Chrome(ChromeDriverManager().install(), options=options)
        
        driver.get(url)
        driver.maximize_window()

        driver.find_element_by_id("MemberContractId").send_keys(login)
        driver.find_element_by_id("MemberPassword").send_keys(password)
        button_click(driver, "ログイン")
        
        logger.debug('collect_autossl: login')
        sleep(3)
        
        driver.find_element_by_xpath('//a[@href="/servers/"]').click()
        
        logger.debug('collect_autossl: go to server_list')
        sleep(3)

        server_no = 1
        while server_no <= 300:
            if server_no > 100 and server_no <= 200:
                driver.find_element_by_link_text(str(2)).click()
            elif server_no > 200:
                driver.find_element_by_link_text(str(3)).click()
            sleep(3)

            login_button = driver.find_elements_by_xpath('//button[@type="submit"]')
            list_no = server_no % 100 - 1
            login_button[list_no].click()
            sleep(4)
            
            driver.switch_to.window(driver.window_handles[1])
            driver.implicitly_wait(200)
            driver.find_element_by_id("username").send_keys(cwp_login)
            driver.find_element_by_id("password").send_keys(password)
            driver.find_element_by_id("btnsubmit").click()

            driver.implicitly_wait(60)
            driver.find_element_by_xpath('//li[@class="searchmenu"][3]').click()
            sleep(2)
            driver.find_element_by_xpath('//a[@href="?module=letsencrypt"]').click()
            write_autossl(driver, server_no)
            sleep(2)

            driver.close()
            driver.switch_to.window(driver.window_handles[0])

            server_no += 1
            
        driver.close()
        driver.quit()
    except Exception as err:
        logger.debug(f'Error: collect_autossl: {err}')
        exit(1)

### main_script ###
if __name__ == '__main__':

    try:
        logger.debug("collect_autossl: start collect_autossl")
        collect_autossl()
        exit(0)
    except Exception as err:
        logger.debug(f'collect_autossl: {err}')
        exit(1)
