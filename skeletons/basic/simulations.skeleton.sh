#!/bin/sh

set_job_state () {
	local job_id=$$$$
	local job_state=$1
	local job_line="$job_id: $job_state"

	local grep_res=''

	if [ -f "$JOBS_STATES_FILENAME" ]; then
		grep_res=`grep -n -m 1 -e "^$job_id:" "$JOBS_STATES_FILENAME"`
	fi

	if [ -z "$grep_res" ]; then
		echo "$job_line" >> "$JOBS_STATES_FILENAME"

	else
		local n=`echo "$grep_res" | cut -d : -f 1`
		sed -i $n"s/.*/$job_line/" "$JOBS_STATES_FILENAME"
	fi
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
