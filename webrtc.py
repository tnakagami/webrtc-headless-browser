import bs4
import logging
import logging.config
import os
import signal
import sys
import threading
import time
from daemon import DaemonContext
from lockfile.pidlockfile import PIDLockFile
from selenium import webdriver

class WebRTC:
    """
    Web Real-Time Communication

    Attributes
    ----------
    __driver : webdriver
    __logger : logging.logger
    __status : boolean
    __max_wait_sec : int
    __event : threading.Event
    """

    def __init__(self, config_name):
        """
        constructor

        Parameters
        ----------
        config_name : str
            config name of logging
        """
        # setup driver
        chrome_option = webdriver.ChromeOptions()
        chrome_option.add_argument('--headless')
        chrome_option.add_argument('--disable-gpu')
        chrome_option.add_argument('--autoplay-policy=no-user-gesture-required')
        self.__driver = webdriver.Chrome(options=chrome_option)
        # setup logger
        self.__logger = logging.getLogger(config_name)
        # setup status and max wait sec
        self.__status = False
        self.__max_wait_sec = 0
        # setup event
        self.__event = threading.Event()

    def initialize(self, max_wait_sec=3600):
        """
        initialize

        Parameters
        ----------
        max_wait_sec : int
            waiting time for repeating url access
            default: 3600 [sec]
        """
        self.__status = True
        self.__max_wait_sec = max_wait_sec
        # output message
        self.__logger.info('=================')
        self.__logger.info('===== Start =====')
        self.__logger.info('=================')

    def finalize(self):
        """
        finalize
        """
        self.__driver.quit()
        # output message
        self.__logger.info('=================')
        self.__logger.info('=====  Stop =====')
        self.__logger.info('=================')

    def get_stream(self):
        """
        get stream of logger
        """
        return self.__logger.handlers[0].stream

    def update_status(self):
        """
        update status
        """
        self.__status = False
        self.__max_wait_sec = 0
        self.__event.set()

    def __run_login_process(self, username, password, base_url):
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
        """
        try:
            self.__logger.info('[start] login process')
            wait_time_sec = 3
            # access login page
            login_url = '{}/index.php'.format(base_url)
            self.__driver.get(login_url)
            time.sleep(wait_time_sec)
            # enter username and password
            username_field = self.__driver.find_element_by_name('username')
            username_field.send_keys(username)
            password_field = self.__driver.find_element_by_name('password')
            password_field.send_keys(password)
            # login process
            login_btn = self.__driver.find_element_by_id('btn-login')
            login_btn.click()
            time.sleep(wait_time_sec)
            self.__logger.info('[ end ] login process')
        except Exception as e:
            _, _, exc_tb = sys.exc_info()
            self.__logger.warn('{} (line: {})'.format(e, exc_tb.tb_lineno))

    def execute(self, username, password):
        """
        thread function
        """
        base_url = os.getenv('WEBRTC_BASE_URL')
        kwargs = {
            'username': username,
            'password': password,
            'base_url': base_url,
        }
        self.__run_login_process(**kwargs)

        while self.__status:
            try:
                # access dashboard
                self.__driver.get('{}/index.php?display=dashboard'.format(base_url))
                soup = bs4.BeautifulSoup(self.__driver.page_source, 'html.parser')
                # check login status
                if soup.h3 is None or soup.h3.text.strip() != 'Welcome {}'.format(username):
                    self.__run_login_process(**kwargs)
                else:
                    self.__logger.info('{}'.format(soup.h3.text))
                # wait for next access...
                self.__event.wait(self.__max_wait_sec)
                self.__event.clear()
            except Exception as e:
                wait_time_sec = 3
                _, _, exc_tb = sys.exc_info()
                self.__logger.warn('{} (line: {})'.format(e, exc_tb.tb_lineno))
                self.__logger.warn('retry after waiting for {} seconds'.format(wait_time_sec))
                # retry after several seconds
                self.__event.wait(wait_time_sec)
                self.__event.clear()

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
    # setup logging configuration
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
    # initialization
    process_status = ProcessStatus()
    signal_map = {
        signal.SIGINT: process_status.change_status,
        signal.SIGTERM: process_status.change_status
    }
    # setup webrtc
    max_wait_sec = 60 * 60 - 7
    webrtc = WebRTC('webrtc')
    pidfile = PIDLockFile('/var/run/lock/webrtc.pid')
    webrtc.initialize(max_wait_sec)

    with DaemonContext(pidfile=pidfile, signal_map=signal_map, working_directory=os.getcwd(), files_preserve=[webrtc.get_stream()]):
        thread = threading.Thread(target=webrtc.execute, args=(os.getenv('WEBRTC_USERNAME'), os.getenv('WEBRTC_PASSWORD'),))
        thread.start()

        # main loop
        while process_status.get_status():
            time.sleep(3)

        webrtc.update_status()
        thread.join()

    # finalization
    webrtc.finalize()
