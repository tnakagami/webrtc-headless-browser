# webrtc-headless-browser
WebRTC using headless browser

## preparetion
* upgrade pip command

    ```sh
    pip3 install --upgrade setuptools pip
    ```
* install pipenv

    ```sh
    sudo pip3 install pipenv
    ```
* install chromium-browser and chromium-chromedriver

    ```sh
    # install chrome
    sudo apt install chromium-browser
    sudo apt install chromium-chromedriver

    # check version
    chromium-browser -version
    # output: Chromium 88.0.4324.187 Built on Raspbian , running on Raspbian 10
    chromedriver --version
    # output: ChromeDriver 88.0.4324.187 (2b6622a6304bb4a5fbb4d7efa5a02d7a663d1cd1-refs/branch-heads/4324@{#2213})
    ```

* create virtual environment

    ```sh
    # check python version using following command
    python3 -V
    # output: Python 3.7.3

    # create virtual environment
    pipenv --python 3.7
    ```

* install libraries

    ```sh
    pipenv install
    ```

## execute python script
Run the following command.

```sh
pipenv run start
```
