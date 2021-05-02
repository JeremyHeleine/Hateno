#!/bin/sh

portfile=`dirname $0`/port
$PATH_TO_HATENO server --save-port "$portfile" $COMMAND_LINES_FILENAME &

while [ ! -f "$portfile" ]; do sleep 0.1; done
port=`cat "$portfile"`

### BEGIN_EXEC ###
$PATH_TO_HATENO exec --port $port --log $LOG_FILENAME &
### END_EXEC ###
