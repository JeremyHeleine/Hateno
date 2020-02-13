#!/bin/sh

### BEGIN_JOB ###
out=`sbatch $ITEM_VALUE`
echo "$out" | cut -d ' ' -f 4
### END_JOB ###
