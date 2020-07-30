#!/bin/sh

set_job_state () {
	local job_id=$$$$
	local job_state=$1

	$PATH_TO_HATENO_JOBS $JOBS_STATES_FILENAME set $job_id $job_state
}

set_job_state running

{
	### BEGIN_COMMAND_LINES ###
	$ITEM_VALUE &&
	### END_COMMAND_LINES ###
	set_job_state succeed
} || {
	set_job_state failed
}
