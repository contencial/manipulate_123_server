import os
import re
import shutil
import dropbox
import gspread
from time import sleep
from ftplib import FTP
from datetime import datetime, timedelta
from dropbox import DropboxOAuth2FlowNoRedirect
from oauth2client.service_account import ServiceAccountCredentials

# Logger setting
from logging import getLogger, FileHandler, DEBUG
logger = getLogger(__name__)
today = datetime.now()
os.makedirs('./log', exist_ok=True)
handler = FileHandler(f'log/{today.strftime("%Y-%m-%d")}_result.log', mode='a')
handler.setLevel(DEBUG)
logger.setLevel(DEBUG)
logger.addHandler(handler)
logger.propagate = False

class Data():
    VGSEO_FOLDER = '/contencial チーム フォルダ/vgseo納品データ'

    def __init__(self):
        self.user = os.environ['SERVER123_FTPUSER']
        self.passwd = os.environ['SERVER123_FTPPASS']
        self.current_server_no = None
        self.current_domain = None
        self.current_file_year = None
        self.current_file_no = None

        scope = ['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/drive']
        credentials = ServiceAccountCredentials.from_json_keyfile_name('spreadsheet.json', scope)
        self.gc = gspread.authorize(credentials)

        rdbx = dropbox.Dropbox(
            oauth2_refresh_token=os.environ['DROPBOX_REFRESH_TOKEN'],
            app_key=os.environ['DROPBOX_APP_KEY'],
            app_secret=os.environ['DROPBOX_APP_SECRET']
        )
        rdbx.refresh_access_token()
        access_token = rdbx._oauth2_access_token
        self.dbx = dropbox.Dropbox(access_token)

        self.get_server_list()
        self.get_upload_list()
        self.get_vgseo_folder_list()

    def get_server_list(self):
        SPREADSHEET_ID = os.environ['SERVERLIST_SSID']
        sheet = self.gc.open_by_key(SPREADSHEET_ID).worksheet('ServerList')
        cell_list = sheet.range('I2:I301')
        server_list = [cell.value for cell in cell_list]
        self.server_list = {}
        for i, s in enumerate(server_list):
            self.server_list[f'{i + 1}'] = s

    def get_upload_list(self):
        SPREADSHEET_ID = os.environ['MANIPULATION_PARAM_SSID']
        sheet = self.gc.open_by_key(SPREADSHEET_ID).worksheet('UploadInfo')
        upload_info = sheet.get_all_values()
        upload_info.pop(0)
        upload_list = []
        for u in upload_info:
            upload_list.append({
                'server_no': u[0],
                'domain': u[1],
                'file_year': u[2],
                'file_no': u[3],
            })
        self.upload_list = sorted(upload_list, key=lambda x: int(x['server_no']))

    def get_vgseo_folder_list(self):
        logger.debug('get_vgseo_folder_list: Start')
        csv_folders = set([u['file_year'] for u in self.upload_list])
        self.vgseo_folder_list = {}

        def process_entries(entries, c):
            for entry in entries:
                if not entry.name == '_uploaded' and isinstance(entry, dropbox.files.FolderMetadata):
                    self.vgseo_folder_list[c].append(entry)

        for c in csv_folders:
            logger.debug(f' > {c}')
            self.vgseo_folder_list[c] = []
            result = self.dbx.files_list_folder(f'{self.VGSEO_FOLDER}/{c}/')
            process_entries(result.entries, c)
            while result.has_more:
                result = self.dbx.files_list_folder_continue(result.cursor)
                process_entries(result.entries, c)

    def ftp_login(self):
        logger.debug(f' > ftp_login: {self.current_server_no} | {self.server_list[self.current_server_no]}')
        self.ftp = FTP(
            host=self.server_list[self.current_server_no],
            user=self.user,
            passwd=self.passwd
        )
        os.makedirs('./tmp/', exist_ok=True)
        with open('./tmp/index.cgi', 'wb') as fp:
            self.ftp.retrbinary('RETR /public_html/UPDATE/index.cgi', fp.write)
        with open('./tmp/robots.txt', 'wb') as fp:
            self.ftp.retrbinary('RETR /public_html/UPDATE/robots.txt', fp.write)
        with open('./tmp/.htaccess', 'wb') as fp:
            self.ftp.retrbinary('RETR /public_html/UPDATE/.htaccess', fp.write)
        with open('./tmp/sitemap.xml', 'wb') as fp:
            self.ftp.retrbinary('RETR /public_html/UPDATE/sitemap.xml', fp.write)
        with open('./tmp/sitemap.xml', 'r+') as fp:
            data = fp.read()
            details = f'<url>\n<loc>https://www.{self.current_domain}/</loc>\n<changefreq>daily</changefreq>\n<priority>1.0</priority>\n</url>\n'
            output = data.replace('{_DETAILS_}', details)
            fp.seek(0)
            fp.write(output)
            fp.truncate()
        self.ftp.cwd('/public_html/')

    def ftp_close(self):
        logger.debug(f' > ftp_close')
        self.ftp.close()
        shutil.rmtree('./tmp/')

    def ftp_upload(self):
        logger.debug(f' > ftp_upload: {self.current_server_no} | {self.current_domain}')
        try:
            path = f'/public_html/{self.current_domain}/'
            try:
                self.ftp.cwd(path)
            except:
                self.ftp.mkd(path)
                self.ftp.cwd(path)
            try:
                self.ftp.mkd('.well-known')
            except:
                pass
            with open('./tmp/index.cgi', 'rb') as fp:
                self.ftp.storbinary('STOR index.cgi', fp)
            self.ftp.sendcmd('SITE CHMOD 755 index.cgi')
            with open('./tmp/robots.txt', 'rb') as fp:
                self.ftp.storbinary('STOR robots.txt', fp)
            with open('./tmp/.htaccess', 'rb') as fp:
                self.ftp.storbinary('STOR .htaccess', fp)
            with open('./tmp/sitemap.xml', 'rb') as fp:
                self.ftp.storbinary('STOR sitemap.xml', fp)
            for entry in self.vgseo_folder_list[self.current_file_year]:
                if entry.name.startswith(f'{self.current_file_no}_'):
                    self.download_vgseo_files(entry.id)
                    self.upload_vgseo_files()
                    break
            self.dbx.files_move(f'{self.VGSEO_FOLDER}/{self.current_file_year}/{entry.name}', f'{self.VGSEO_FOLDER}/{self.current_file_year}/_uploaded/{entry.name}')
        except Exception as e:
            logger.debug(f'ftp_upload: {self.current_server_no}:{self.current_domain}: {e}')

    def download_vgseo_files(self, folder_id):
        logger.debug(' >> download_vgseo_files')
        os.makedirs('./tmp/vgseo/', exist_ok=True)
        result = self.dbx.files_list_folder(folder_id, recursive=True)

        assert(result.entries[0].id==folder_id)
        common_dir = result.entries[0].path_lower

        def process_entries(entries):
            for entry in entries:
                if isinstance(entry, dropbox.files.FileMetadata):
                    path = f'./tmp/vgseo/{entry.path_lower.removeprefix(common_dir)}'
                    if path.endswith('.html'):
                        path = path.removesuffix('.html') + '.tpl'
                    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
                    self.dbx.files_download_to_file(path, entry.path_lower)

        process_entries(result.entries)
        while result.has_more:
            result = self.dbx.files_list_folder_continue(result.cursor)
            process_entries(result.entries)

    def upload_vgseo_files(self):
        logger.debug(' >> upload_vgseo_files')
        for root, dirs, files in os.walk('tmp/vgseo/'):
            path = f'/public_html/{self.current_domain}/{root.removeprefix("tmp/vgseo/")}'
            try:
                self.ftp.cwd(path)
            except:
                self.ftp.mkd(path)
                self.ftp.cwd(path)
            for f in files:
                with open(os.path.join(root, f), 'rb') as fp:
                    self.ftp.storbinary(f"STOR {f}", fp)
        shutil.rmtree('./tmp/vgseo/')


### main_script ###
if __name__ == '__main__':
    try:
        logger.debug("\n\nFTP_UPLOAD: Start get_domain_info\n\n")
        d = Data()
        if len(d.upload_list) == 0:
            logger.debug("ftp_upload: no remove target")
            exit(0)
        logger.debug("ftp_upload: start uploading")
        for i, u in enumerate(d.upload_list):
            logger.info(f'ftp_upload: {u["server_no"]} | {u["domain"]} | {u["file_year"]} | {u["file_no"]}')
            d.current_domain = u['domain']
            d.current_file_year = u['file_year']
            d.current_file_no = u['file_no']
            if not d.current_server_no == u['server_no']:
                d.current_server_no = u['server_no']
                if hasattr(d, 'ftp'):
                    d.ftp_close()
                d.ftp_login()
            d.ftp_upload()
        d.ftp_close()
    except Exception as err:
        logger.debug(f'ftp_upload: {err}')
        if 'd' in locals():
            d.ftp_close()
        exit(1)