#!/bin/sh

### BEGIN_JOB ###
out=`sbatch $ITEM_VALUE`
echo ${JOBS_IDS__$ITEM_INDEX}
### END_JOB ###
