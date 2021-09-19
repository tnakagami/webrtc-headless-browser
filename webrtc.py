import bs4
import time
import signal
import threading
import os
from selenium import webdriver
from daemon import DaemonContext
from lockfile.pidlockfile import PIDLockFile

class WebRTC(threading.Thread):
    """
    Web Real-Time Communication

    Attributes
    ----------
    event : threading.Event
    """

    def __init__(self, max_wait_sec=3600):
        """
        constructor

        Parameters
        ----------
        max_wait_sec : int
            waiting time for repeating url access
            default: 3600 [sec]
        """
        super().__init__()
        self.status= True
        self.max_wait_sec = max_wait_sec
        self.event = threading.Event()

    def change_status(self, signum, frame):
        """
        change status

        Parameters
        ----------
        signum : int
            signal number
        frame : str
            frame information
        """
        self.status = False
        self.event.set()

    def run(self):
        """
        thread function
        """
        base_url = os.getenv('WEBRTC_BASE_URL')
        wait_time_sec = 3
        # setup driver
        chrome_option = webdriver.ChromeOptions()
        chrome_option.add_argument('--headless')
        chrome_option.add_argument('--disable-gpu')
        chrome_option.add_argument('--autoplay-policy=no-user-gesture-required')
        driver = webdriver.Chrome(options=chrome_option)

        # access login page
        login_url = '{}/index.php'.format(base_url)
        driver.get(login_url)
        time.sleep(wait_time_sec)
        # enter username and password
        username_field = driver.find_element_by_name('username')
        username_field.send_keys(os.getenv('WEBRTC_USERNAME'))
        password_field = driver.find_element_by_name('password')
        password_field.send_keys(os.getenv('WEBRTC_PASSWORD'))
        # login process
        login_btn = driver.find_element_by_id('btn-login')
        login_btn.click()
        time.sleep(wait_time_sec)

        # access dashboard
        access_url = '{}/index.php?display=dashboard'.format(base_url)
        while self.status:
            driver.get(access_url)
            soup = bs4.BeautifulSoup(driver.page_source, 'html.parser')
            print(soup.h3)
            self.event.wait(self.max_wait_sec)
            self.event.clear()

        driver.quit()

if __name__ == '__main__':
    # initialization
    max_wait_sec = 60 * 60
    webrtc = WebRTC(max_wait_sec=max_wait_sec)
    signal_map = {
        signal.SIGINT, webrtc.change_status,
        signal.SIGTERM, webrtc.change_status,
    }

    with DaemonContext(pidfile=PIDLockFile('/var/run/webrtc.pid'), signal_map=signal_map) as context:
        webrtc.start()

        # main loop
        while webrtc.status:
            time.sleep(1)

        # finalization
        webrtc.join()
