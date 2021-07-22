#!/bin/sh

$HATENO server --log $LOG_FILENAME $COMMAND_LINES_FILENAME $JOB_DIRECTORY > /dev/null 2>&1 &
