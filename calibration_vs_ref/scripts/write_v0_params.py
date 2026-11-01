#!/usr/bin/env python3
"""Write the SeaSTAR V0 calibration into a campaign's L1.0/setup/calibration.sh.

Reads v0_seastar.txt from transfer_v0.py and the tempcorr_<site>.txt files from fit_tempcorr.py, and
writes, between BEGIN and END marker lines (replacing any block already there, or added at the end of
the file the first time), everything L1.0 needs to turn a darksub_quad voltage into an optical depth
consistently with how V0 was transferred:

    V0_TREF=30                        the temperature the V0s are about
    V0_TEMP_CORR_A_CH<n>, _B_CH<n>    the scatter-method quadratic coefficients, the mean over the sites
                                      (transfer_v0.py corrected each site with its own)
    V0_INTERCEPT_CH<n>, V0_INTERCEPT_A_CH<n>
                                      the weighted-mean intercept-line V0 and intercept a
    V0_ORIGIN_CH<n>                   the weighted-mean V0 of the line through the origin
    V0_CHANNELS                       the channels with a V0, separated by spaces

for |V|corr = |V| / (1 + A*dT + B*dT^2), dT = T - V0_TREF, and tau * airmass = ln((V0 - a) / (|V|corr - a)),
with the intercept V0 and a (V0_MODE=intercept in L1.0), or the origin V0 and a = 0 (V0_MODE=origin).
"""

import argparse
import re
import sys
from pathlib import Path

METHOD = "SCATTER"
DARK = "DARKSUB_QUAD"
BEGIN = "# BEGIN V0 calibration (written by calibration_vs_ref/scripts/write_v0_params.py)"
END = "# END V0 calibration"


def read_values(path):
    return dict(line.strip().split("=", 1) for line in open(path) if "=" in line and not line.startswith("#"))


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("calibration", help="the campaign's L1.0/setup/calibration.sh, edited in place (made if missing)")
    p.add_argument("v0", help="v0_seastar.txt from transfer_v0.py")
    p.add_argument("fits", nargs="+", help="tempcorr_<site>.txt files from fit_tempcorr.py (averaged)")
    args = p.parse_args()

    v0 = read_values(args.v0)
    channels = sorted(int(m.group(1)) for key in v0 if (m := re.fullmatch(r"V0_SEASTAR_INTERCEPT_CH(\d+)", key)))
    if not channels:
        sys.exit(f"no V0_SEASTAR_INTERCEPT_CH<n> lines in {args.v0}")
    sites = [(re.sub(r"[^A-Z0-9]+", "_", Path(f).stem.removeprefix("tempcorr_").upper()), read_values(f))
             for f in args.fits]
    trefs = {float(v["TEMPCORR_TREF"]) for _tag, v in sites} | {float(v0["V0_SEASTAR_TREF"])}
    if len(trefs) != 1:
        sys.exit(f"the fits and the V0s have different reference temperatures: {sorted(trefs)}")

    def mean(name):
        return sum(float(v[f"TEMPCORR_{tag}_{METHOD}_{DARK}_QUAD_{name}"]) for tag, v in sites) / len(sites)

    lines = [BEGIN,
             f"# intercept-line V0 and a, and origin-line V0, from {Path(args.v0).name}, the weighted mean of the sites; scatter-method",
             f"# quadratic darksub_quad temperature coefficients, the mean of {', '.join(Path(f).name for f in args.fits)}",
             f"V0_TREF={trefs.pop():g}",
             f"V0_CHANNELS=\"{' '.join(str(ch) for ch in channels)}\""]
    names = ["V0_TREF", "V0_CHANNELS"]
    for ch in channels:
        values = {f"V0_INTERCEPT_CH{ch}": float(v0[f"V0_SEASTAR_INTERCEPT_CH{ch}"]),
                  f"V0_INTERCEPT_A_CH{ch}": float(v0[f"V0_SEASTAR_INTERCEPT_A_CH{ch}"]),
                  f"V0_ORIGIN_CH{ch}": float(v0[f"V0_SEASTAR_ORIGIN_CH{ch}"]),
                  f"V0_TEMP_CORR_A_CH{ch}": mean(f"A_CH{ch}"),
                  f"V0_TEMP_CORR_B_CH{ch}": mean(f"B_CH{ch}")}
        lines += [f"{name}={value:.6e}" for name, value in values.items()]
        names += list(values)
    lines += [f"export {' '.join(names[i:i + 6])}" for i in range(0, len(names), 6)]
    lines.append(END)
    block = "\n".join(lines) + "\n"

    path = Path(args.calibration)
    text = path.read_text() if path.exists() else ""
    if BEGIN in text:
        text = re.sub(re.escape(BEGIN) + r".*?" + re.escape(END) + r"\n", lambda _m: block, text, flags=re.S)
    else:
        text = text.rstrip("\n") + ("\n\n" if text else "") + block
    path.write_text(text)
    print(f"wrote V0s for ch{', ch'.join(str(ch) for ch in channels)} into {path}")


if __name__ == "__main__":
    main()
