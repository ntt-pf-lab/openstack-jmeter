#!/bin/bash

data_dir=$1
users_file=$data_dir/users.csv
tenants_file=$data_dir/tenants.csv
output_file='user_tenants.csv'

echo "Data Directory is: $data_dir"

usr_count=`wc -l $users_file|awk '{print $1}'`
ten_count=`wc -l $tenants_file|awk '{print $1}'`

if [ $ten_count -le $usr_count ]
then
    while read -r -u3 line1 ; read -r -u4 line2; do pass=`echo $line1|sed "s/user/password/"` ; echo "$line1,$pass,$line2" >> $data_dir/$output_file; done 3< "$users_file" 4< "$tenants_file"
else
    while read -r -u3 line1 ; read -r -u4 line2; do pass=`echo $line1|sed "s/user/password/"` ; echo "$line1,$pass,$line2" >> $data_dir/$output_file; done 3< "$tenants_file" 4< "$users_file"
fi
