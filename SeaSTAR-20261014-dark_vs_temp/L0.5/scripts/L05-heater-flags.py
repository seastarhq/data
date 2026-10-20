#!/usr/bin/env python3

# sets the HEATER_ON user flag (L05line['flags'][7]) on every L05 timestep that falls
# within the heater-on times in the notes file, plus a margin either side of them.
# Usable data is when the heater is off, i.e. timesteps without this flag.

from datetime import datetime,timedelta
import sys, os, re
import numpy as np
import pytz
import argparse

# custom modules:
import seastar_datautils
from seastar_error_flags import *

# where to find things:
# including
# ROOT_DIR SCRIPTS_DIR RAW_DATA_DIR EXTRACTED_DATA_DIR PICKLE_DIR
from seastar_filepaths import *

# the notes are written by hand as "HH:MM[:SS] heater on/off", in local time,
# and "heater" is sometimes misspelled (hetaer, hetare), so we only ask for a word starting with "he"
NOTES_HEATER = re.compile(r"^\s*(\d{1,2}):(\d{2})(?::(\d{2}))?\s+he\w*\s+(on|off)\b", re.I)

USER_FLAGS = 7  # index of the user-set flags in L05line['flags']

parser = argparse.ArgumentParser()
parser.add_argument('file')
parser.add_argument('-n', '--notesfile', help='defaults to notes_<YYYYMMDD>.txt in RAW_DATA_DIR')
parser.add_argument('-m', '--margin', type=float, default=45.0,
                    help='seconds flagged either side of each heater-on period (default 45)')
parser.add_argument('-o', '--outputfile', help='defaults to overwriting the input L05 file')
args = parser.parse_args()

def read_heater_periods(notesfile, date, timezone):
    # returns a list of (on, off) pairs as naive UTC datetimes, to match the L05 datetimes
    periods = []
    on_time = None
    with open(notesfile) as notes:
        for line in notes:
            match = NOTES_HEATER.match(line)
            if match is None:
                continue
            hh, mm, ss, state = match.groups()
            local_time = timezone.localize(datetime.combine(date, datetime.min.time())
                                           + timedelta(hours=int(hh), minutes=int(mm), seconds=int(ss or 0)))
            utc_time = local_time.astimezone(pytz.utc).replace(tzinfo=None)
            if state.lower() == 'on':
                if on_time is not None:
                    sys.stderr.write(f"heater on at {on_time} with no note of it going off before {utc_time}\n")
                on_time = utc_time
            else:
                if on_time is None:
                    sys.stderr.write(f"heater off at {utc_time} with no note of it going on, ignored\n")
                    continue
                periods.append((on_time, utc_time))
                on_time = None
    if on_time is not None:  # the notes never say it went off again
        sys.stderr.write(f"heater still on at {on_time}, no note of it going off: flagging to the end of the data\n")
        periods.append((on_time, datetime.max))
    return periods

raw_data_dirs = [PICKLE_DIR,]
L05file = seastar_datautils.findFile(args.file,raw_data_dirs)

if args.outputfile is None:
    output_filename = L05file
else:
    output_filename = PICKLE_DIR + '/' + args.outputfile

L05_data = np.load(L05file, allow_pickle=True)
metadata = L05_data['metadata'][()]
L05_array = L05_data['array_data']

seastar_timezone = pytz.timezone(metadata['SEASTAR_TIMEZONE'])
L05file_date = datetime.strptime(os.path.basename(L05file).split('_')[1], '%Y-%m-%d').date()  # assuming a naming convention here...

if args.notesfile is None:
    notesfile = seastar_datautils.findFile('notes_' + L05file_date.strftime('%Y%m%d') + '.txt', [RAW_DATA_DIR,])
else:
    notesfile = seastar_datautils.findFile(args.notesfile, [RAW_DATA_DIR, '.'])

heater_periods = read_heater_periods(notesfile, L05file_date, seastar_timezone)
margin = timedelta(seconds=args.margin)

# a timestep is flagged if any of its datapoints fall inside a heater period plus margin.
# the unused datapoints in each timestep are NaT, which never compare as inside.
datetimes = L05_array['datetime']
heater_on = np.zeros(datetimes.shape, dtype=bool)
for on_time, off_time in heater_periods:
    start = np.datetime64(on_time - margin, 'ms')
    end = np.datetime64(min(off_time, datetime.max - margin) + margin, 'ms')
    heater_on |= (datetimes >= start) & (datetimes <= end)
    sys.stderr.write(f"heater on {on_time} to {off_time} UTC, flagging {start} to {end}\n")
heater_timesteps = heater_on.any(axis=1)

# clear any earlier heater flags first, so rerunning with a different margin or notes doesn't leave stale flags
L05_array['flags'][:, USER_FLAGS] &= ~HEATER_ON
L05_array['flags'][heater_timesteps, USER_FLAGS] |= HEATER_ON

sys.stderr.write(f"flagged {heater_timesteps.sum()} of {len(L05_array)} timesteps as HEATER_ON\n")

metadata['NOTES_FILE'] = os.path.basename(notesfile)
metadata['HEATER_MARGIN'] = args.margin
metadata['HEATER_PERIODS_UTC'] = [(on.isoformat(), off.isoformat()) for on, off in heater_periods]
metadata['L05-heater-flags_PROCESSING_TIME'] = datetime.now(pytz.utc).isoformat()

with open(output_filename, 'bw') as arrayfile:
    np.savez(arrayfile, array_data = L05_array, metadata = metadata)
