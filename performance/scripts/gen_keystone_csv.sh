#!/bin/bash

test_data_dir=$1
csv_file=$2
test_data=$3
test_data2=${4:-}

if [ ! -e $test_data_dir ]; then
    mkdir -p $test_data_dir
fi

if [ -z $test_data2 ]
then
    echo "Unset" >> /dev/null
    echo $test_data >> $test_data_dir/$csv_file
else
    echo "set">> /dev/null
    echo "$test_data,$test_data2" >> $test_data_dir/$csv_file
fi
