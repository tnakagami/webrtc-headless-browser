import bs4
import logging
import logging.config
import os
import queue
import schedule
import signal
import sys
import threading
import time
import re
from daemon import DaemonContext
from lockfile.pidlockfile import PIDLockFile
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException

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
    __implicitly_wait_time : int
    __whitelist : list
    __wait : WebDriverWait
    """

    def __init__(self, config_name, username, password, implicitly_wait_time=5, whitelist=None):
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
        implicitly_wait_time : int
            implicitly wait time
            default: 5
        whitelist : list or None
            white list of incoming call
            default: ['*68'] # wakeup call
        """
        # setup logger
        self.__logger = logging.getLogger(config_name)
        # setup login information
        self.__base_url = os.getenv('WEBRTC_BASE_URL')
        self.__username = username
        self.__password = password
        self.__implicitly_wait_time = implicitly_wait_time
        self.__whitelist = ['*68'] if whitelist is None else whitelist

    def initialize(self):
        """
        initialize
        """
        # setup driver
        chrome_option = webdriver.ChromeOptions()
        chrome_option.add_argument('--headless')
        chrome_option.add_argument('--disable-gpu')
        chrome_option.add_argument('--use-fake-device-for-media-stream')
        chrome_option.add_argument('--use-fake-ui-for-media-stream')
        chrome_option.add_argument('--autoplay-policy=no-user-gesture-required')
        self.__driver = webdriver.Chrome(options=chrome_option)
        self.__wait = None
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
            self.__logger.warning('{} (line: {})'.format(e, exc_tb.tb_lineno))

    def chk_login_status(self):
        """
        check login status
        """
        is_running = True

        while is_running:
            try:
                # access dashboard
                access_url = '{}/index.php?display=dashboard'.format(self.__base_url)
                self.__driver.get(access_url)
                soup = bs4.BeautifulSoup(self.__driver.page_source, 'html.parser')
                # check login status
                if soup.h3 is None or soup.h3.text.strip() != 'Welcome {}'.format(self.__username):
                    self.__run_login_process()
                    self.__driver.get(access_url)
                else:
                    self.__logger.info('{}'.format(soup.h3.text.strip()))
                # enable phone widget
                self.__driver.find_element_by_xpath("//a[@data-widget_type_id='phone' and @data-name='Phone']").click()
                self.__wait = WebDriverWait(self.__driver, self.__implicitly_wait_time)
                is_running = False
            except Exception as e:
                wait_time_sec = 3
                _, _, exc_tb = sys.exc_info()
                self.__logger.warning('{} (line: {})'.format(e, exc_tb.tb_lineno))
                self.__logger.warning('retry after waiting for {} seconds'.format(wait_time_sec))
                # retry after several seconds
                time.sleep(wait_time_sec)

    def chk_specific_incoming_call(self):
        """
        check specific incoming call
        """
        try:
            element = self.__driver.find_element_by_xpath("//div[@class='contactImage' and contains(@style,'did')]")
            button = self.__wait.until(EC.element_to_be_clickable((By.XPATH, "//button[text()='Answer']")))
            # check specific incoming call
            if element:
                attribute_value = element.get_attribute('style')
                matched = re.search('(?<=did=)[0-9\*]+', attribute_value)
                # the case of did is contained in white list
                if matched and matched.group() in self.__whitelist:
                    button.click()
        except (NoSuchElementException, TimeoutException):
            # ignore exception
            pass
        except Exception as e:
            _, _, exc_tb = sys.exc_info()
            self.__logger.warning('{} (line: {})'.format(e, exc_tb.tb_lineno))

class JobWorker(threading.Thread):
    """
    Job Worker

    Attributes
    ----------
    __queue : queue.Queue
    __is_running : boolean
    """

    def __init__(self):
        """
        constructor
        """
        super().__init__()
        self.__queue = queue.Queue()
        self.__is_running = True

    def put(self, job):
        """
        put job
        """
        self.__queue.put(job)

    def clear(self):
        """
        clear queue
        """
        with self.__queue.mutex:
            self.__queue.queue.clear()

    def finish(self):
        """
        finish job worker
        """
        self.__is_running = False

    def run(self):
        """
        thread function
        """
        while self.__is_running:
            try:
                job = self.__queue.get(block=True, timeout=1)
                job()
                self.__queue.task_done()
            except queue.Empty:
                pass

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
    implicitly_wait_time = 10
    webrtc = WebRTC('webrtc', os.getenv('WEBRTC_USERNAME'), os.getenv('WEBRTC_PASSWORD'), implicitly_wait_time=implicitly_wait_time-1, whitelist=['001', '99003', '*68'])
    pidfile = PIDLockFile('/var/run/lock/webrtc.pid')
    webrtc.initialize()
    job_worker = JobWorker()

    with DaemonContext(pidfile=pidfile, signal_map=signal_map, working_directory=os.getcwd(), files_preserve=[webrtc.get_stream()]):
        # setup schedule
        job_worker.put(webrtc.chk_login_status)
        schedule.every().day.at('00:03').do(job_worker.put, webrtc.chk_login_status)
        schedule.every().hour.at('00:01').do(job_worker.clear)
        schedule.every(implicitly_wait_time+1).seconds.do(job_worker.put, webrtc.chk_specific_incoming_call)
        job_worker.start()

        # main loop
        while process_status.get_status():
            schedule.run_pending()
            time.sleep(0.1)

        # clear schedule
        schedule.clear()
        # finish job worker
        job_worker.finish()
        job_worker.join()

    # finalization
    webrtc.finalize()
