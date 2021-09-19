import bs4
import time
import signal
import threading
import os
import logging
import logging.config
from selenium import webdriver
from daemon import DaemonContext
from lockfile.pidlockfile import PIDLockFile

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

    def __run_login_process(self, username, password, base_url, driver):
        """
        run login process

        Parameters
        ----------
        username : str
            login username
        password : str
            login password
        base_url : str
            base url
        driver : webdriver
            instance of webdriver
        """
        self.logger.info('[start] login process')
        wait_time_sec = 3
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
        self.logger.info('[ end ] login process')

    def execute(self, username, password):
        """
        thread function
        """
        self.logger.info('== Start ===')
        base_url = os.getenv('WEBRTC_BASE_URL')
        # setup driver
        chrome_option = webdriver.ChromeOptions()
        chrome_option.add_argument('--headless')
        chrome_option.add_argument('--disable-gpu')
        chrome_option.add_argument('--autoplay-policy=no-user-gesture-required')
        driver = webdriver.Chrome(options=chrome_option)
        kwargs = {
            'username': username,
            'password': password,
            'base_url': base_url,
            'driver': driver,
        }
        self.__run_login_process(**kwargs)

        # access dashboard
        access_url = '{}/index.php?display=dashboard'.format(base_url)
        while self.status:
            driver.get(access_url)
            soup = bs4.BeautifulSoup(driver.page_source, 'html.parser')
            if soup.h3 is None or soup.h3.text.strip() != 'Welcome {}'.format(username):
                self.__run_login_process(**kwargs)
            else:
                self.logger.info('{}: {}'.format(username, soup.h3.text))
            self.event.wait(self.max_wait_sec)
            self.event.clear()

        driver.quit()
        self.logger.info('== Stop ===')

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
    signal_map = {
        signal.SIGINT: process_status.change_status,
        signal.SIGTERM: process_status.change_status
    }
    # setup webrtc
    max_wait_sec = 60 * 60
    webrtc = WebRTC('webrtc', max_wait_sec=max_wait_sec)
    pidfile = PIDLockFile('/var/run/lock/webrtc.pid')

    with DaemonContext(pidfile=pidfile, signal_map=signal_map, working_directory=os.getcwd(), files_preserve=[webrtc.logger.handlers[0].stream]):
        thread = threading.Thread(target=webrtc.execute, args=(os.getenv('WEBRTC_USERNAME'), os.getenv('WEBRTC_PASSWORD'),))
        thread.start()

        # main loop
        while process_status.get_status():
            time.sleep(3)

        # finalization
        webrtc.update_status()
        thread.join()
