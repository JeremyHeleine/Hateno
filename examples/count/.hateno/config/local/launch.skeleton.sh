#!/bin/sh

port=`cat "$PORT_FILENAME"`

### BEGIN_EXEC ###
$HATENO exec --port $port > /dev/null 2>&1 &
### END_EXEC ###
