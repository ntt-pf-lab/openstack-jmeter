#!/bin/bash

FILE=$1

if [[ ! -a $FILE ]]; then
    rm -rf $FILE
fi

if [[ -L $FILE ]]; then
   rm -rf $FILE
fi
