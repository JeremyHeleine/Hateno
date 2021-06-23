#!/bin/sh

### FOR K FROM 1 TO $N_EXEC
$HATENO exec $JOB_DIRECTORY > /dev/null 2>&1 &
###
