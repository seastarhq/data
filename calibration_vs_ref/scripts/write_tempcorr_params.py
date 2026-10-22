#!/usr/bin/env python3
"""Write the L0.6 temperature-correction coefficients into a campaign's L0.6/setup/parameters.sh.

Reads one or more tempcorr_<site>.txt files written by fit_tempcorr.py and takes one method's
coefficients (default residual) for both dark-subtracted voltages and both orders. With more than
one file, each coefficient is the mean over the sites. The block is written between BEGIN and END
marker lines, replacing any block already there, or added before the export lines at the end of
the file (with its exports after them) the first time:

    TEMP_CORR_TREF=30
    TEMP_CORR_DARKSUB_QUAD_LIN_A_CH<n>=...
    TEMP_CORR_DARKSUB_QUAD_QUAD_A_CH<n>=...   TEMP_CORR_DARKSUB_QUAD_QUAD_B_CH<n>=...
    (and the same for DARKSUB_LIN)

TEMP_CORR_ORDER, which picks the linear or quadratic coefficients, is set by hand in parameters.sh
and isn't touched.
"""

import argparse
import re
import sys
from pathlib import Path

DARKS = ("DARKSUB_LIN", "DARKSUB_QUAD")
BEGIN = "# BEGIN temperature-correction coefficients (written by calibration_vs_ref/scripts/write_tempcorr_params.py)"
END = "# END temperature-correction coefficients"
EXPORT_BEGIN = "# BEGIN temperature-correction exports"
EXPORT_END = "# END temperature-correction exports"


def read_values(path):
    return dict(line.strip().split("=", 1) for line in open(path) if "=" in line and not line.startswith("#"))


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("parameters", help="the campaign's L0.6/setup/parameters.sh, edited in place")
    p.add_argument("fits", nargs="+", help="tempcorr_<site>.txt files from fit_tempcorr.py (several are averaged)")
    p.add_argument("--method", default="residual", help="which fit's coefficients (default residual)")
    args = p.parse_args()

    sites, values = [], []
    for path in args.fits:
        site = Path(path).stem.removeprefix("tempcorr_")
        sites.append(site)
        values.append((re.sub(r"[^A-Z0-9]+", "_", site.upper()), read_values(path)))
    trefs = {float(v["TEMPCORR_TREF"]) for _tag, v in values}
    if len(trefs) != 1:
        sys.exit(f"the fits have different reference temperatures: {sorted(trefs)}")

    def mean(name):
        return sum(float(v[f"TEMPCORR_{tag}_{args.method.upper()}_{name}"]) for tag, v in values) / len(values)

    how = sites[0] if len(sites) == 1 else "the mean of " + " and ".join(sites)
    lines = [BEGIN,
             f"# {args.method} fits from {', '.join(Path(f).name for f in args.fits)}: {how}",
             "# Vcorr = V / (1 + A*dT) for TEMP_CORR_ORDER=lin, V / (1 + A*dT + B*dT^2) for quad, dT = T - TEMP_CORR_TREF",
             f"TEMP_CORR_TREF={trefs.pop():g}"]
    names = ["TEMP_CORR_TREF"]
    for dark in DARKS:
        for ch in range(1, 11):
            for name in (f"{dark}_LIN_A_CH{ch}", f"{dark}_QUAD_A_CH{ch}", f"{dark}_QUAD_B_CH{ch}"):
                lines.append(f"TEMP_CORR_{name}={mean(name):.6e}")
                names.append(f"TEMP_CORR_{name}")
    lines.append(END)
    exports = [EXPORT_BEGIN] + [f"export {' '.join(names[i:i + 6])}" for i in range(0, len(names), 6)] + [EXPORT_END]

    text = Path(args.parameters).read_text()
    block = "\n".join(lines) + "\n"
    export_block = "\n".join(exports) + "\n"
    if BEGIN in text:
        text = re.sub(re.escape(BEGIN) + r".*?" + re.escape(END) + r"\n", lambda _m: block, text, flags=re.S)
        text = re.sub(re.escape(EXPORT_BEGIN) + r".*?" + re.escape(EXPORT_END) + r"\n", lambda _m: export_block,
                      text, flags=re.S)
    else:
        first_export = re.search(r"^export ", text, re.M)
        text = text[:first_export.start()] + block + "\n\n" + text[first_export.start():]
        text = text.rstrip("\n") + "\n" + export_block
    Path(args.parameters).write_text(text)
    print(f"wrote {how} {args.method} coefficients into {args.parameters}")


if __name__ == "__main__":
    main()
