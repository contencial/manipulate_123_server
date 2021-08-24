import os
import re
import datetime
import gspread
from ftplib import FTP
from oauth2client.service_account import ServiceAccountCredentials

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
def get_ftp_server_info():
    SPREADSHEET_ID = os.environ['SERVERLIST_SSID']
    scope = ['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/drive']
    credentials = ServiceAccountCredentials.from_json_keyfile_name('spreadsheet.json', scope)
    gc = gspread.authorize(credentials)
    sheet = gc.open_by_key(SPREADSHEET_ID).worksheet('ServerList')

    cell_list = sheet.range('I1:I301')
    ftp_server_list = [cell.value for cell in cell_list]
    return ftp_server_list

def get_domain_info():
    SPREADSHEET_ID = os.environ['MANIPULATION_PARAM_SSID']
    scope = ['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/drive']
    credentials = ServiceAccountCredentials.from_json_keyfile_name('spreadsheet.json', scope)
    gc = gspread.authorize(credentials)
    sheet = gc.open_by_key(SPREADSHEET_ID).worksheet('RemoveInfoFtp')

    domain_info = sheet.get_all_values()
    domain_info.pop(0)
    return domain_info

def remove_ftp_dir(domain, host, user, passwd):
    ftp = FTP(
            host=host,
            user=user,
            passwd=passwd
        )
    ftp.rename(f'/public_html/{domain}', f'/_old/{domain}')
    
### main_script ###
if __name__ == '__main__':

    user = os.environ['SERVER123_FTPUSER']
    passwd = os.environ['SERVER123_FTPPASS']
    try:
        logger.debug("remove_ftp_dir: start get_domain_info")
        ftp_server_list = get_ftp_server_info()
        domain_info = get_domain_info()
        if len(domain_info) == 0:
            logger.debug("remove_ftp_dir: no remove target")
            exit(0)
        logger.debug("remove_ftp_dir: start remove_domain_info")
        for element in domain_info:
            server_no = int(element[0])
            host = element[1]
            logger.info(f'{server_no}, {host}, {user}, {passwd}')
            remove_ftp_dir(host, ftp_server_list[server_no], user, passwd)
        exit(0)
    except Exception as err:
        logger.debug(f'remove_ftp_dir: {err}')
        exit(1)
