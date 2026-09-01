#!/usr/bin/env python3
# read the raw Hamburger data into a pandas dataframe, keeping only the J3
# radiometer channels and the block temperatures, then make a second dataframe
# of 1-second averages and pickle it.

from datetime import datetime, timedelta
import argparse
import glob
import os
import re
import sys

import pandas as pd

# what the notes file tells us about the state of the test. the notes are
# written to the minute, and an event can run a little either side of the time
# it was noted at, so disturbances are flagged over a window around that time.
NOTES_TIME = re.compile(r"^\s*(\d{1,2}):(\d{2})\s+(\S.*)")
HEATER_ON = re.compile(r"heater\s+on|turn(?:ing)?\s+on\s+(?:the\s+)?heater", re.I)
HEATER_OFF = re.compile(r"heater\s+off|turn(?:ing)?\s+off\s+(?:the\s+)?heater", re.I)
LAMP_ON = re.compile(r"lamp\s+on|turn(?:ing)?\s+on\s+(?:the\s+)?lamp", re.I)
LAMP_OFF = re.compile(r"lamp\s+off|turn(?:ing)?\s+off\s+(?:the\s+)?lamp", re.I)
DISTURBANCES = [("door", re.compile(r"door", re.I)),
                ("darks", re.compile(r"dark", re.I))]
DISTURBANCE_WINDOW = 90  # seconds either side of the noted time

# the columns we care about for the temperature test:
TIME_COLUMN = "HH:MM:SS"
DATA_COLUMNS = ["J3_CH1_0", "J3_CH2_0", "J3_CH3_0", "J3_CH4_0", "J3_CH5_0",
                "J3_CH1_2", "J3_CH2_2", "J3_CH3_2", "J3_CH4_2", "J3_CH5_2",
                "Temp1", "Temp2", "Temp3", "Temp4"]

# the raw files carry a few lines of preamble (filename, title, author) before
# the header line, and split(1) parts after the first have no header at all,
# so we look for the header rather than assuming a fixed number of skiprows.
PREAMBLE_SEARCH_LINES = 20


def find_raw_files(raw_dir):
    """Return the raw file(s) to read, in time order.

    Prefers a single concatenated file; falls back to the split parts.
    """
    whole = sorted(glob.glob(os.path.join(raw_dir, "HamburgerData_*.txt")))
    whole += sorted(glob.glob(os.path.join(raw_dir, "HamburgerData_*.txt-raw*")))
    if whole:
        return whole[:1]

    parts = sorted(glob.glob(os.path.join(raw_dir, "HamburgerData_*.txt_part_*")))
    if parts:
        return parts

    sys.stderr.write(f"no raw HamburgerData files found in {raw_dir}\n")
    sys.exit(1)


def find_header(datafile):
    """Return (column names, number of lines to skip) for one raw file.

    Returns (None, 0) for a file with no header line, i.e. a split part.
    """
    with open(datafile) as f:
        for linenumber, line in enumerate(f):
            if line.startswith(TIME_COLUMN + ","):
                return line.strip().split(","), linenumber + 1
            if linenumber > PREAMBLE_SEARCH_LINES:
                break
    return None, 0


def read_raw(datafiles):
    """Read the raw file(s) into one dataframe, keeping only our columns."""
    columns = None
    frames = []

    for datafile in datafiles:
        fileheader, skiprows = find_header(datafile)
        if fileheader is not None:
            columns = fileheader
        if columns is None:
            sys.stderr.write(f"no header line found before {datafile}\n")
            sys.exit(1)

        missing = [c for c in [TIME_COLUMN] + DATA_COLUMNS if c not in columns]
        if missing:
            sys.stderr.write(f"columns missing from {datafile}: {missing}\n")
            sys.exit(1)

        sys.stderr.write(f"reading {os.path.basename(datafile)}\n")
        frames.append(pd.read_csv(datafile,
                                  skiprows=skiprows,
                                  header=None,
                                  names=columns,
                                  usecols=[TIME_COLUMN] + DATA_COLUMNS,
                                  on_bad_lines="warn"))

    # keep the columns in the order we asked for, not the order in the file:
    return pd.concat(frames, ignore_index=True)[[TIME_COLUMN] + DATA_COLUMNS]


def find_notes(raw_dir):
    """Return the notes file for the test, or None if there isn't one."""
    notes = sorted(glob.glob(os.path.join(raw_dir, "notes*.txt")))
    if not notes:
        return None
    return notes[0]


def read_notes(notesfile, startdate):
    """Read the notes file into a list of (timestamp, text).

    The notes only carry a time of day, like the data, so they get the same
    treatment: the date comes from the data file and we roll over to the next
    day if the times ever go backwards.
    """
    notes = []
    day = timedelta(0)
    previous = timedelta(-1)

    with open(notesfile) as f:
        for line in f:
            match = NOTES_TIME.match(line)
            if match is None:
                continue
            timeofday = timedelta(hours=int(match.group(1)),
                                  minutes=int(match.group(2)))
            if timeofday < previous:
                day += timedelta(days=1)
            previous = timeofday
            notes.append((startdate + day + timeofday, match.group(3).strip()))

    return notes


def lamp_state_at_start(notes):
    """Was the lamp on when the test started?

    Nobody writes down the state things were already in, so we work it out from
    the first note about the lamp: if it was switched off during the test it
    must have been on to begin with, and the other way around.
    """
    for _, text in notes:
        if LAMP_OFF.search(text):
            return True
        if LAMP_ON.search(text):
            return False

    sys.stderr.write("no note about the lamp: taking it to have been on "
                     "throughout\n")
    return True


def add_note_flags(df, notes, window):
    """Add the heater state and disturbance columns, from the notes.

    heater_on is True from a noted "heater on" until the matching "heater off".
    lamp_on holds the state of the lamp: it is taken to have been on from the
    start of the test unless the first note about it says it was switched on.
    disturbance names anything that upsets the measurement (the room door being
    opened, darks being taken) over a window either side of the noted time, and
    is empty the rest of the time; rows within more than one get both names.
    """
    df["heater_on"] = False
    df["lamp_on"] = lamp_state_at_start(notes)
    df["disturbance"] = ""

    window = timedelta(seconds=window)
    heater_on_time = None

    for notetime, text in notes:
        if HEATER_OFF.search(text):
            if heater_on_time is not None:
                df.loc[heater_on_time:notetime, "heater_on"] = True
                heater_on_time = None
        elif HEATER_ON.search(text):
            heater_on_time = notetime

        if LAMP_OFF.search(text):
            df.loc[notetime:, "lamp_on"] = False
        elif LAMP_ON.search(text):
            df.loc[notetime:, "lamp_on"] = True

        for label, pattern in DISTURBANCES:
            if pattern.search(text) is None:
                continue
            disturbed = ((df.index >= notetime - window)
                         & (df.index <= notetime + window))
            df.loc[disturbed, "disturbance"] = [
                    label if not existing else existing + "," + label
                    for existing in df.loc[disturbed, "disturbance"]]

    if heater_on_time is not None:  # the notes never say it went off again
        sys.stderr.write(f"heater still on at {heater_on_time}, no note of it "
                         "going off\n")
        df.loc[heater_on_time:, "heater_on"] = True

    return df


def file_date(datafile):
    """Pull the date out of a HamburgerData_YYYY_MM_DD_HH_MM_SS filename."""
    match = re.search(r"(\d{4})_(\d{2})_(\d{2})", os.path.basename(datafile))
    if match is None:
        sys.stderr.write(f"no date in filename {datafile}, using 1970-01-01\n")
        return datetime(1970, 1, 1)
    return datetime(int(match.group(1)), int(match.group(2)), int(match.group(3)))


def add_datetime(df, startdate):
    """Turn the HH:MM:SS column into a datetime index.

    The raw files only record time of day, so we take the date from the
    filename and roll over to the next day if the clock ever goes backwards.
    """
    timeofday = pd.to_timedelta(df[TIME_COLUMN])
    days = (timeofday.diff() < timedelta(0)).cumsum()
    df["datetime"] = startdate + timeofday + pd.to_timedelta(days, unit="D")
    df.drop(TIME_COLUMN, axis=1, inplace=True)
    df.set_index("datetime", inplace=True)
    return df


def main():
    scripts_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(scripts_dir)

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="*",
                        help="raw data file(s); default is whatever is in ../raw")
    parser.add_argument("-r", "--raw-dir", default=os.path.join(root_dir, "raw"),
                        help="directory to look for raw data in")
    parser.add_argument("-o", "--outputfile",
                        help="pickle file to write the 1-second averages to")
    parser.add_argument("-i", "--interval", default="1s",
                        help="averaging interval (pandas offset, default 1s)")
    parser.add_argument("-n", "--notes",
                        help="notes file; default is notes*.txt in the raw dir")
    parser.add_argument("-w", "--disturbance-window", type=int,
                        default=DISTURBANCE_WINDOW,
                        help="seconds either side of a noted disturbance to flag")
    parser.add_argument("--full-outputfile",
                        help="also pickle the full-rate dataframe here")
    args = parser.parse_args()

    datafiles = args.files if args.files else find_raw_files(args.raw_dir)

    df = read_raw(datafiles)
    df = add_datetime(df, file_date(datafiles[0]))

    # the 1-second averages, before the flag columns get added, so that we are
    # only ever averaging the measurements:
    df_avg = df.resample(args.interval).mean()

    notesfile = args.notes if args.notes else find_notes(args.raw_dir)
    if notesfile is None:
        sys.stderr.write("no notes file found: "
                         "heater_on and disturbance will be empty\n")
        notes = []
    else:
        sys.stderr.write(f"reading {os.path.basename(notesfile)}\n")
        notes = read_notes(notesfile, file_date(datafiles[0]))

    for frame in (df, df_avg):
        add_note_flags(frame, notes, args.disturbance_window)

    if args.outputfile is None:
        basename = os.path.basename(datafiles[0]).split(".")[0]
        pickle_dir = os.path.join(root_dir, "pickle")
        os.makedirs(pickle_dir, exist_ok=True)
        outputfile = os.path.join(pickle_dir, f"{basename}_{args.interval}avg.pkl")
    else:
        outputfile = args.outputfile

    df_avg.to_pickle(outputfile)

    lamp_off_time = (~df_avg["lamp_on"]).sum() * pd.Timedelta(args.interval)
    if lamp_off_time:
        sys.stderr.write(f"lamp off for {lamp_off_time}\n")

    heater_time = df_avg["heater_on"].sum() * pd.Timedelta(args.interval)
    disturbed_time = (df_avg["disturbance"] != "").sum() * pd.Timedelta(args.interval)
    sys.stderr.write(f"heater on for {heater_time}, "
                     f"disturbances flagged for {disturbed_time}\n")

    sys.stderr.write(f"{len(df)} raw samples from {df.index[0]} to {df.index[-1]}\n")
    sys.stderr.write(f"{len(df_avg)} {args.interval} averages written to {outputfile}\n")

    if args.full_outputfile is not None:
        df.to_pickle(args.full_outputfile)
        sys.stderr.write(f"full-rate dataframe written to {args.full_outputfile}\n")


if __name__ == "__main__":
    main()
