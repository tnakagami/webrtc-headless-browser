import bs4
import time
import signal
import threading
import os
import logging
import logging.config
import daemon
from selenium import webdriver

class WebRTC:
    """
    Web Real-Time Communication

    Attributes
    ----------
    status : boolean
    logger : logging.logger
    max_wait_sec : int
    event : threading.Event
    """

    def __init__(self, config_name, max_wait_sec=3600):
        """
        constructor

        Parameters
        ----------
        config_name : str
            config name of logging
        max_wait_sec : int
            waiting time for repeating url access
            default: 3600 [sec]
        """
        super().__init__()
        self.status= True
        self.logger = logging.getLogger(config_name)
        self.max_wait_sec = max_wait_sec
        self.event = threading.Event()

    def update_status(self):
        """
        update status
        """
        self.status = False
        self.event.set()

    def execute(self, username, password):
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
        username_field.send_keys(username)
        password_field = driver.find_element_by_name('password')
        password_field.send_keys(password)
        # login process
        login_btn = driver.find_element_by_id('btn-login')
        login_btn.click()
        time.sleep(wait_time_sec)

        # access dashboard
        access_url = '{}/index.php?display=dashboard'.format(base_url)
        while self.status:
            driver.get(access_url)
            soup = bs4.BeautifulSoup(driver.page_source, 'html.parser')
            self.logger.info('{}: {}'.format(username, soup.h3.text))
            self.event.wait(self.max_wait_sec)
            self.event.clear()

        driver.quit()

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
    # initialization
    logging.config.dictConfig({
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'infoFormat': {
                'format': '[%(asctime)s %(levelname)s] %(name)s %(message)s',
                'datefmt': '%Y/%m/%d %H:%M:%S'
            }
        },
        'handlers': {
            'timeRotate': {
                'class': 'logging.handlers.TimedRotatingFileHandler',
                'formatter': 'infoFormat',
                'filename': '/var/log/webrtc/status.log',
                'when': 'W2',
                'backupCount': 5
            },
            'consoleHandler': {
                'class': 'logging.StreamHandler',
                'formatter': 'infoFormat'
            }
        },
        'loggers': {
            'webrtc': {
                'level': 'INFO',
                'handlers': ['timeRotate', 'consoleHandler']
            }
        }
    })
    process_status = ProcessStatus()
    signal.signal(signal.SIGINT, process_status.change_status)
    signal.signal(signal.SIGTERM, process_status.change_status)
    pidfile = daemon.pidfile.PIDLockFile('/var/run/webrtc.pid')

    if not pidfile.is_locked():
        with daemon.DaemonContext(working_directory=os.getcwd(), pidfile=pidfile):
            max_wait_sec = 60 * 60
            webrtc = WebRTC('webrtc', max_wait_sec=max_wait_sec)
            thread = threading.Thread(target=webrtc.execute, args=(os.getenv('WEBRTC_USERNAME'), os.getenv('WEBRTC_PASSWORD'),))
            thread.start()

            # main loop
            while process_status.get_status():
                time.sleep(3)

            # finalization
            webrtc.update_status()
            thread.join()
