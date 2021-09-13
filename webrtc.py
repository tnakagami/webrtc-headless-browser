import bs4
import time
import signal
import threading
import os
from selenium import webdriver

class WebRTC(threading.Thread):
    def __init__(self, process_status):
        super().__init__()
        self.process_status = process_status
        chrome_option = webdriver.ChromeOptions()
        chrome_option.add_argument('--headless')
        chrome_option.add_argument('--disable-gpu')
        self.driver = webdriver.Chrome(options=chrome_option)

    def __del__(self):
        self.driver.quit()

    def run(self):
        base_url = os.getenv('WEBRTC_BASE_URL')
        wait_time_sec = 5

        # access login page
        login_url = '{}/index.php'.format(base_url)
        self.driver.get(login_url)
        time.sleep(wait_time_sec)
        self.driver.save_screenshot('/home/pi/ss01.png')
        # enter username and password
        username_field = self.driver.find_element_by_name('username')
        username_field.send_keys(os.getenv('WEBRTC_USERNAME'))
        password_field = self.driver.find_element_by_name('password')
        password_field.send_keys(os.getenv('WEBRTC_PASSWORD'))
        self.driver.save_screenshot('/home/pi/ss02.png')
        # login process
        login_btn = self.driver.find_element_by_id('btn-login')
        login_btn.click()
        time.sleep(wait_time_sec * 2)
        self.driver.save_screenshot('/home/pi/ss03.png')
        # access dashboard
        access_url = '{}/index.php?display=dashboard'.format(base_url)
        while self.process_status.get_status():
            self.driver.get(access_url)
            soup = bs4.BeautifulSoup(self.driver.page_source, 'html.parser')
            print(soup.h3)
            time.sleep(60)
        self.driver.close()

class ProcessStatus():
    """
    プロセスの状態
    Attributes
    ----------
    __status : bool
        True  : 実行中
        False : 停止中
    """

    def __init__(self):
        """
        コンストラクタ
        """
        self.__status = True

    def change_status(self, signum, frame):
        """
        ステータスの変更
        Parameters
        ----------
        signum : int
            シグナル番号
        frame : str
            フレーム情報
        """
        self.__status = False

    def get_status(self):
        """
        現在のステータスの取得
        """
        return self.__status

if __name__ == '__main__':
    # ================================
    # プロセス監視用インスタンスの生成
    # ================================
    process_status = ProcessStatus()
    signal.signal(signal.SIGINT, process_status.change_status)
    signal.signal(signal.SIGTERM, process_status.change_status)

    webrtc = WebRTC(process_status)
    webrtc.start()

    while process_status.get_status():
        time.sleep(3)

    webrtc.join()
