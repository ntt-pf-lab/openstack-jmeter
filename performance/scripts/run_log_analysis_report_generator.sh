#!/bin/bash

echo "Arguments to log analysis report are:\n"
echo $@

python /home/rohit/openstack-jmeter/performance/scripts/log_analysis_report_generator.py $@
