#!/usr/bin/env python3
"""
Assemble the per-session "too big for github" raw log files into one CSV.

Each session log starts with an identical header line followed by rows in
which most fields are still 0 while the system spins up.  This tool:

  * finds every *too-big-for-github / *too_big_for_github file in a directory
    (or takes explicit files), sorted by the timestamp in the filename
  * checks all headers agree, and writes the header once
  * per file, drops leading rows until the first row where every column is
    nonzero, ignoring columns that are zero for the whole file (e.g. q3, cq*)
    plus anything passed with --ignore
  * optionally splits the result into GitHub-sized _part_NN chunks

Usage:
  assemble_raw.py raw/
  assemble_raw.py raw/*too-big* -o raw/2026-09-14_log.csv --split
"""

import argparse
import os
import re
import sys

# Matches "...-raw_too-big_for_github", "...-raw_too_big_for_github", etc.
tooBigPattern = re.compile(r"too[-_]big[-_]for[-_]github$")

# Leading "YYYY-MM-DD" of a session log filename.
datePattern = re.compile(r"^(\d{4}-\d{2}-\d{2})")


def log(msg, quiet=False):
	if not quiet:
		print(msg, file=sys.stderr)


def findInputs(paths):
	"""Expand directories into their too-big files; return a sorted list."""
	files = []

	for p in paths:
		if os.path.isdir(p):
			for name in os.listdir(p):
				if tooBigPattern.search(name):
					files.append(os.path.join(p, name))
		elif os.path.isfile(p):
			files.append(p)
		else:
			sys.exit(f"error: no such file or directory: {p}")

	# Filenames start with YYYY-MM-DD_HH-MM-SS so alphabetical == chronological.
	return sorted(set(files), key=os.path.basename)


def defaultOutput(files):
	dates = set()

	for f in files:
		match = datePattern.match(os.path.basename(f))
		if not match:
			sys.exit(f"error: cannot derive a date from {os.path.basename(f)}; use --output")
		dates.add(match.group(1))

	if len(dates) != 1:
		sys.exit(f"error: inputs span several dates ({', '.join(sorted(dates))}); use --output")

	return os.path.join(os.path.dirname(files[0]), f"{dates.pop()}_log.csv")


def parseHeader(line):
	return [name.strip() for name in line.rstrip("\n").split(",")]


def splitRow(line):
	return [x.strip() for x in line.rstrip("\n").split(",")]


def firstCompleteRow(rows, names, ignore, quiet):
	"""
	Return the index of the first row where every column not in `ignore`
	(and not zero for the whole file) is nonzero, or None if there is none.
	"""
	ncol = len(names)
	parsed = []
	alwaysZero = [True] * ncol

	for i, line in enumerate(rows):
		v = splitRow(line)
		if len(v) != ncol:
			log(f"    warning: row {i + 2} has {len(v)} fields, expected {ncol}; skipping it", quiet)
			parsed.append(None)
			continue
		parsed.append(v)
		for j, x in enumerate(v):
			if alwaysZero[j] and x != "0":
				alwaysZero[j] = False

	autoIgnored = [names[j] for j in range(ncol) if alwaysZero[j] and names[j] not in ignore]
	if autoIgnored:
		log(f"    always-zero columns ignored: {', '.join(autoIgnored)}", quiet)

	check = [j for j in range(ncol) if not alwaysZero[j] and names[j] not in ignore]

	for i, v in enumerate(parsed):
		if v is not None and all(v[j] != "0" for j in check):
			return i, parsed

	return None, parsed


def writeParts(outPath, lines, partSize, quiet):
	nparts = 0

	for start in range(0, len(lines), partSize):
		partPath = f"{outPath}_part_{nparts:02d}"
		with open(partPath, "w") as f:
			f.writelines(lines[start:start + partSize])
		nparts += 1

	log(f"wrote {nparts} part files of up to {partSize} lines: {outPath}_part_NN", quiet)


def main():
	parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
	parser.add_argument("inputs", nargs="+", help="directory containing too-big files, and/or explicit files")
	parser.add_argument("-o", "--output", help="output CSV (default: <date>_log.csv next to the inputs)")
	parser.add_argument("--ignore", default="", help="comma-separated columns to ignore in the nonzero check, in addition to always-zero ones")
	parser.add_argument("--split", nargs="?", const=15000, type=int, metavar="LINES",
	                    help="also write <output>_part_NN chunks of LINES lines (default 15000) for committing to GitHub")
	parser.add_argument("--force", action="store_true", help="overwrite an existing output file")
	parser.add_argument("-q", "--quiet", action="store_true", help="suppress the per-file summary")
	args = parser.parse_args()

	files = findInputs(args.inputs)
	if not files:
		sys.exit("error: no too-big-for-github files found")

	outPath = args.output or defaultOutput(files)
	if os.path.exists(outPath) and not args.force:
		sys.exit(f"error: {outPath} exists; use --force to overwrite")

	ignore = {c.strip() for c in args.ignore.split(",") if c.strip()}

	header = None
	outLines = []
	totalKept = 0
	totalDropped = 0

	for path in files:
		name = os.path.basename(path)
		with open(path) as f:
			thisHeader = parseHeader(f.readline())
			rows = f.readlines()

		if header is None:
			header = thisHeader
			outLines.append(", ".join(header) + "\n")
		elif thisHeader != header:
			sys.exit(f"error: header of {name} differs from {os.path.basename(files[0])}; refusing to mix schemas")

		unknown = ignore - set(header)
		if unknown:
			sys.exit(f"error: --ignore column(s) not in header: {', '.join(sorted(unknown))}")

		log(f"{name}:", args.quiet)
		start, parsed = firstCompleteRow(rows, header, ignore, args.quiet)

		if start is None:
			log("    warning: no complete row found; keeping the whole file", args.quiet)
			start = 0

		kept = [line for line, v in zip(rows[start:], parsed[start:]) if v is not None]
		dropped = len(rows) - len(kept)
		outLines.extend(kept)
		totalKept += len(kept)
		totalDropped += dropped
		log(f"    dropped {dropped} spin-up rows, kept {len(kept)}", args.quiet)

	with open(outPath, "w") as f:
		f.writelines(outLines)

	log(f"wrote {outPath}: {totalKept} data rows from {len(files)} files ({totalDropped} rows dropped)", args.quiet)

	if args.split is not None:
		writeParts(outPath, outLines, args.split, args.quiet)


if __name__ == "__main__":
	main()
