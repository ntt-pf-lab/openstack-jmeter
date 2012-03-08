#!/bin/bash

echo "ARGUMENTS TO PERF ANALYZER ARE\n"
echo $@

python /home/rohit/openstack-jmeter/performance/scripts/nova_api_perf_analyzer.py $@
