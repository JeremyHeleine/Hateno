#!/bin/sh

port=`cat "$PORT_FILENAME"`

### FOR K FROM 1 TO $N_EXEC
$HATENO exec --port $port > /dev/null 2>&1 &
###
