#!/usr/bin/env python3


from datetime import datetime,timedelta
import sys
import os
import re

#datetime_pattern = r'^\d{4}.*' #-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}.*'
datetime_pattern = r'^(?P<time>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})[.]\d{9}.*'
regex = re.compile(datetime_pattern)

def round_to_the_last_x_min(timestamp,x):
    return timestamp - (timestamp - timestamp.min) % timedelta(minutes=x)

def round_to_the_next_x_min(timestamp,x):
    return timestamp + (timestamp - timestamp.min) % timedelta(minutes=x)

def get_first_line_with_datetime(filename):
    datetime_pattern = r'^(?P<time>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})[.]\d{9}.*'
    regex = re.compile(datetime_pattern)
    with open(filename, 'r') as f:
    
        firstline = f.readline() #.decode() in binary mode
        #sys.stderr.write(f"{firstline}")
        match = regex.match(firstline)

        if match:
            pass
            #sys.stdout.write(f"{match.group('time')}")
            return match.group("time")

        else:
            while not match:
                line = f.readline()
                match = regex.match(line)
            #print(f"{match.group("time")}")
            return match.group("time")



def get_last_line_with_datetime(filename):
    """this function will probably need some work to generalize"""
    with open(filename, 'rb') as f:
        try:
            f.seek(-2, os.SEEK_END)
            while f.read(1) != b'\n':
                f.seek(-2, os.SEEK_CUR)
            line = f.readline().decode()
            match = regex.match(line)

            if match:
                return match.group("time")

        except OSError: # the file has only one line...
            f.seek(0)



filename = sys.argv[1]

firsttime = datetime.fromisoformat(get_first_line_with_datetime(filename))
lasttime = datetime.fromisoformat(get_last_line_with_datetime(filename))

firsttime = round_to_the_last_x_min(firsttime,1)
lasttime = round_to_the_next_x_min(lasttime,1)

sys.stdout.write(f"{firsttime.isoformat()}/{lasttime.isoformat()}\n")

