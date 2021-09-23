import bs4
import logging
import logging.config
import os
import schedule
import signal
import sys
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
    __base_url : str
    __username : str
    __password : str
    """

    def __init__(self, config_name, username, password):
        """
        constructor

        Parameters
        ----------
        config_name : str
            config name of logging
        username : str
            login username
        password : str
            login password
        """
        # setup logger
        self.__logger = logging.getLogger(config_name)
        # setup login information
        self.__base_url = os.getenv('WEBRTC_BASE_URL')
        self.__username = username
        self.__password = password

    def initialize(self):
        """
        initialize
        """
        # setup driver
        chrome_option = webdriver.ChromeOptions()
        chrome_option.add_argument('--headless')
        chrome_option.add_argument('--disable-gpu')
        chrome_option.add_argument('--autoplay-policy=no-user-gesture-required')
        self.__driver = webdriver.Chrome(options=chrome_option)
        # output message
        self.__logger.info('Initialization')

    def finalize(self):
        """
        finalize
        """
        self.__driver.quit()
        # output message
        self.__logger.info('Finalization')

    def get_stream(self):
        """
        get stream of logger
        """
        return self.__logger.handlers[0].stream

    def __run_login_process(self):
        """
        run login process
        """
        try:
            self.__logger.info('[start] login process')
            wait_time_sec = 3
            # access login page
            self.__driver.get('{}/index.php'.format(self.__base_url))
            time.sleep(wait_time_sec)
            # enter username and password
            username_field = self.__driver.find_element_by_name('username')
            username_field.send_keys(self.__username)
            password_field = self.__driver.find_element_by_name('password')
            password_field.send_keys(self.__password)
            # login process
            login_btn = self.__driver.find_element_by_id('btn-login')
            login_btn.click()
            time.sleep(wait_time_sec)
            self.__logger.info('[ end ] login process')
        except Exception as e:
            _, _, exc_tb = sys.exc_info()
            self.__logger.warn('{} (line: {})'.format(e, exc_tb.tb_lineno))

    def job(self):
        """
        thread function
        """
        is_running = True

        while is_running:
            try:
                # access dashboard
                self.__driver.get('{}/index.php?display=dashboard'.format(self.__base_url))
                soup = bs4.BeautifulSoup(self.__driver.page_source, 'html.parser')
                # check login status
                if soup.h3 is None or soup.h3.text.strip() != 'Welcome {}'.format(self.__username):
                    self.__run_login_process()
                else:
                    self.__logger.info('{}'.format(soup.h3.text.strip()))
                is_running = False
            except Exception as e:
                wait_time_sec = 3
                _, _, exc_tb = sys.exc_info()
                self.__logger.warn('{} (line: {})'.format(e, exc_tb.tb_lineno))
                self.__logger.warn('retry after waiting for {} seconds'.format(wait_time_sec))
                # retry after several seconds
                time.sleep(wait_time_sec)

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
    webrtc = WebRTC('webrtc', os.getenv('WEBRTC_USERNAME'), os.getenv('WEBRTC_PASSWORD'))
    pidfile = PIDLockFile('/var/run/lock/webrtc.pid')
    webrtc.initialize()

    with DaemonContext(pidfile=pidfile, signal_map=signal_map, working_directory=os.getcwd(), files_preserve=[webrtc.get_stream()]):
        # setup schedule
        schedule.every().day.at('0:03').do(webrtc.job)
        # first execution
        webrtc.job()
        # main loop
        while process_status.get_status():
            schedule.run_pending()
            time.sleep(1)

    # finalization
    webrtc.finalize()
