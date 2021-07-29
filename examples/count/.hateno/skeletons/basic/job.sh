#!/bin/sh

### FOR K FROM 1 TO $N_JOB
$HATENO job $COMMAND_LINES_FILENAME $JOB_DIRECTORY > /dev/null 2>&1 &
###
