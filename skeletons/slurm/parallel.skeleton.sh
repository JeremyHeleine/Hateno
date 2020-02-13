#!/bin/sh

case $OMPI_COMM_WORLD_RANK in
	### BEGIN_COMMAND_LINES ###
	$ITEM_INDEX)
		$ITEM_VALUE
		;;
	### END_COMMAND_LINES ###
esac
