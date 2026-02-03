#!/usr/bin/env python3

import sys,os

class Error(Exception): pass

def _find(pathname, dirnames, matchFunc=os.path.isfile):
    """looks for files in a list of directories"""
    for dirname in dirnames:
        candidate = os.path.join(dirname, pathname)
        #sys.stderr.write(candidate)
        print(candidate)
        if matchFunc(candidate):
            return candidate
    raise Error("Can't find file %s" % candidate)

def findFile(pathname,dirnames):
    return _find(pathname,dirnames)

#def findDir(path):
#    return _find(path, matchFunc=os.path.isdir)


