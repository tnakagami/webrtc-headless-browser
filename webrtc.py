import bs4
import time
import signal
import threading
import os
from selenium import webdriver

class WebRTC(threading.Thread):
    """
    Web Real-Time Communication

    Attributes
    ----------
    process_status : ProcessStatus
        instance of ProcessStatus
    driver : webdriver
    event : threading.Event
    """

    def __init__(self, process_status, max_wait_sec=3600):
        """
        constructor

        Parameters
        ----------
        process_status : ProcessStatus
            instance of ProcessStatus
        """
        super().__init__()
        self.process_status = process_status
        chrome_option = webdriver.ChromeOptions()
        chrome_option.add_argument('--headless')
        chrome_option.add_argument('--disable-gpu')
        chrome_option.add_argument('--autoplay-policy=no-user-gesture-required')
        self.max_wait_sec = max_wait_sec
        self.driver = webdriver.Chrome(options=chrome_option)
        self.event = threading.Event()

    def is_event_set(self):
        self.event.set()

    def run(self):
        """
        thread function
        """
        base_url = os.getenv('WEBRTC_BASE_URL')
        wait_time_sec = 5

        # access login page
        login_url = '{}/index.php'.format(base_url)
        self.driver.get(login_url)
        time.sleep(wait_time_sec)
        # enter username and password
        username_field = self.driver.find_element_by_name('username')
        username_field.send_keys(os.getenv('WEBRTC_USERNAME'))
        password_field = self.driver.find_element_by_name('password')
        password_field.send_keys(os.getenv('WEBRTC_PASSWORD'))
        # login process
        login_btn = self.driver.find_element_by_id('btn-login')
        login_btn.click()
        time.sleep(wait_time_sec * 2)
        # access dashboard
        access_url = '{}/index.php?display=dashboard'.format(base_url)
        while self.process_status.get_status():
            self.driver.get(access_url)
            soup = bs4.BeautifulSoup(self.driver.page_source, 'html.parser')
            print(soup.h3)
            self.event.wait(self.max_wait_sec)
            self.event.clear()

        self.driver.quit()

class ProcessStatus():
    """
    Process Status

    Attributes
    ----------
    __status : bool
        True  : running
        False : stopped
    """

    def __init__(self):
        """
        constructor
        """
        self.__status = True

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
        self.__status = False

    def get_status(self):
        """
        get current status
        """
        return self.__status

if __name__ == '__main__':
    process_status = ProcessStatus()
    signal.signal(signal.SIGINT, process_status.change_status)
    signal.signal(signal.SIGTERM, process_status.change_status)

    # initialization
    max_wait_sec = 60 * 60
    webrtc = WebRTC(process_status, max_wait_sec=max_wait_sec)
    webrtc.start()

    # main loop
    while process_status.get_status():
        time.sleep(3)

    # finalization
    webrtc.is_event_set()
    webrtc.join()
