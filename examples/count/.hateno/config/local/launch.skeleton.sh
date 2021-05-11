#!/bin/sh

portfile=`dirname $0`/port
$PATH_TO_HATENO server --save-port "$portfile" --log $LOG_FILENAME $COMMAND_LINES_FILENAME > /dev/null 2>&1 &

while [ ! -f "$portfile" ]; do sleep 0.1; done
port=`cat "$portfile"`

### BEGIN_EXEC ###
$PATH_TO_HATENO exec --port $port > /dev/null 2>&1 &
### END_EXEC ###
