#!/bin/sh

### BEGIN_SIMULATIONS ###
$ITEM_VALUE >> $JOBS_OUTPUT_FILENAME 2>&1 &
echo ${JOBS_IDS__$ITEM_INDEX}
### END_SIMULATIONS ###
