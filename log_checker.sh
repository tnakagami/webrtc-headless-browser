#!/bin/bash

readonly LOGFILE_PATH=/var/log/webrtc
readonly LOG_FILENAME=status.log

ls -t ${LOGFILE_PATH}/${LOG_FILENAME}* | tac | xargs cat -n
