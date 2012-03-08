#!/bin/bash

timestamp_dir=$1
reports_dir=$2

echo "Creating Reports directory '$reports_dir/$timestamp_dir'"
mkdir -p $reports_dir/$timestamp_dir/jtls
mkdir -p $reports_dir/$timestamp_dir/stats

echo "Writing current timestamp to CSV"
echo $timestamp_dir > $reports_dir/curr_timestamp.csv
