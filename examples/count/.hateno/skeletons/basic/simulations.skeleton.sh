#!/bin/sh

$PATH_TO_HATENO_JOBS $JOBS_STATES_FILENAME set $JOB_ID running
$PATH_TO_HATENO_JOBS $JOBS_STATES_FILENAME steps $JOB_ID $COMMAND_LINES_LENGTH

{
	### BEGIN_COMMAND_LINES ###
	$ITEM_VALUE &&
	$PATH_TO_HATENO_JOBS $JOBS_STATES_FILENAME progress $JOB_ID +1 &&
	### END_COMMAND_LINES ###
	$PATH_TO_HATENO_JOBS $JOBS_STATES_FILENAME set $JOB_ID succeed
} || {
	$PATH_TO_HATENO_JOBS $JOBS_STATES_FILENAME set $JOB_ID failed
}
