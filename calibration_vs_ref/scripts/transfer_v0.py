#!/usr/bin/env python3
"""Transfer AERONET's V0 calibration to SeaSTAR, per channel, from the AERONET <-> SeaSTAR matches.

For each site (a matched pickle written by match_aeronet_seastar.py, and its tempcorr_<site>.txt from
fit_tempcorr.py), the SeaSTAR voltages (darksub_quad) are temperature corrected with the site's scatter-
method quadratic coefficients,
    Vcorr = |V| / (1 + A*dT + B*dT^2),   dT = T - TEMPCORR_TREF
and a straight line is fitted to them against the AERONET triplet mean, in two ways:
  origin      Vcorr = b * V_aeronet               V0_seastar = b * V0_aeronet
  intercept   Vcorr = a + b * V_aeronet           V0_seastar = a + b * V0_aeronet
(the intercept line is the one plot_response.py draws; extrapolating it out to V0 carries the intercept
along). V0_aeronet is from the calibration file the pickle records (calibrs_for_<instrument>.txt), and
the AERONET voltages were corrected to its 25 C reference by read_aeronet_tempcorr.py, so V0_seastar is
the SeaSTAR voltage at the top of the atmosphere, at 1 AU and at TREF. Both instruments see the same sun
at the same time, so the earth-sun distance cancels in the slope.

The sites' V0s are combined by an inverse-variance weighted mean, with the standard errors from the line
fits. These are statistical only: the errors in the temperature coefficients and in AERONET's V0 are
not included, and the spread between the sites is the better guide to the real uncertainty.

Only channels matched to a measured AERONET wavelength with a V0 are done: ch4 (550 nm, matched to an
interpolated voltage) and ch8/ch9 (940 nm, matched to the 935 nm water-vapour band, where a Langley V0
doesn't transfer) are skipped, and ch10 (1020 nm) uses the Si detector, as the temperature coefficients do.

Output, -o: a table of every fit, and parameters.sh-style lines
    V0_SEASTAR_<SITE>_<FIT>_CH<n>      each site's
    V0_SEASTAR_<FIT>_CH<n>             the weighted mean,     <FIT> ORIGIN or INTERCEPT
    V0_SEASTAR_<SITE>_INTERCEPT_A_CH<n>, V0_SEASTAR_INTERCEPT_A_CH<n>
                                       the intercept line's a, each site's and the weighted mean. the intercept
                                       line says only |V| - a is proportional to the sun, so an optical depth
                                       from the intercept V0 is ln((V0 - a) / (|V| - a)) / airmass
"""

import argparse
import pickle
import re
import sys
from pathlib import Path

import numpy as np

from fit_tempcorr import pair_data
from plot_matched import matched_pairs
from plot_response import read_coeffs, DARK

METHOD = "scatter"
ORDER = 2
FITS = ("origin", "intercept")
# matched stems that get no V0: interpolated, water vapour, and the InGaAs 1020 (the Si one is used)
SKIP_STEMS = {"V*_550interp", "V*_935", "V*_1020_InGaAs"}
# the calibration file's wavelengths are each instrument's measured centres (0.674 on 905, 0.676 on 608),
# so they're matched to the nearest stem within this
WAVELENGTH_TOL_NM = 10.0


def read_v0(path):
    """{v_stem: V0} from a calibrs_for_<instrument>.txt. 'In' marks the InGaAs 1020."""
    v0 = {}
    in_table = False
    for line in open(path):
        if line.startswith("Wave("):
            in_table = True
            continue
        if not in_table or not line.strip():
            continue
        parts = [p.strip() for p in line.split("\t")]
        ingaas = parts[0].endswith("In")
        nm = float(parts[0].removesuffix("In")) * 1000.0
        stems = {340: "V*_340", 380: "V*_380", 440: "V*_440", 500: "V*_500", 675: "V*_675",
                 870: "V*_870", 935: "V*_935", 1020: "V*_1020", 1640: "V*_1640"}
        wl = min(stems, key=lambda w: abs(w - nm))
        if abs(wl - nm) > WAVELENGTH_TOL_NM:
            sys.exit(f"wavelength {parts[0]} in {path} is not near any AERONET band")
        v0[stems[wl] + ("_InGaAs" if ingaas else "")] = float(parts[1])
    return v0


def fit_origin(x, y):
    """y = b*x: slope and its standard error."""
    b = np.sum(x * y) / np.sum(x * x)
    s2 = np.sum((y - b * x) ** 2) / (len(x) - 1)
    return b, np.sqrt(s2 / np.sum(x * x))


def fit_intercept(x, y):
    """y = a + b*x: (a, b) and their covariance."""
    (b, a), cov = np.polyfit(x, y, 1, cov=True)
    return a, b, cov[::-1, ::-1]  # in (a, b) order


def site_v0(matched_path, coeffs_path):
    """The site, its calibration file, and {ch: row} for every channel with a V0."""
    with open(matched_path, "rb") as fh:
        matched = pickle.load(fh)
    data, metadata = matched["data"], matched["metadata"]
    site = metadata.get("aeronet_site") or Path(matched_path).stem.replace("matched_", "")
    calibration = metadata["aeronet_calibration"]
    v0_aeronet = read_v0(calibration)
    tref, coeffs = read_coeffs(coeffs_path, site, METHOD, ORDER)

    rows = {}
    used = np.zeros(len(data), dtype=bool)  # the matches any channel was fitted with
    for ch, wl, v_stem in matched_pairs(metadata["channel_wavelengths"]):
        if v_stem in SKIP_STEMS:
            continue
        seastar, aeronet, temp, ok = pair_data(data, ch, wl, v_stem, DARK)
        if ok.sum() < 3:
            print(f"  {site} ch{ch}: only {ok.sum()} matches, skipped")
            continue
        used |= ok
        A, B = coeffs.get(ch, (0.0, 0.0))
        dT = temp[ok] - tref
        x, y = aeronet[ok], seastar[ok] / (1.0 + A * dT + B * dT ** 2)
        V0a = v0_aeronet[v_stem]
        b0, b0_err = fit_origin(x, y)
        a, b, cov = fit_intercept(x, y)
        jac = np.array([1.0, V0a])
        rows[ch] = {
            "wl": wl, "v_stem": v_stem, "n": int(ok.sum()), "V0_aeronet": V0a,
            "extrapolation": V0a / x.max(),
            "origin": {"b": b0, "V0": b0 * V0a, "err": b0_err * V0a,
                       "rms": np.std(y / (b0 * x) - 1.0)},
            "intercept": {"a": a, "a_err": np.sqrt(cov[0, 0]), "b": b, "V0": a + b * V0a,
                          "err": np.sqrt(jac @ cov @ jac),
                          "rms": np.std(y / (a + b * x) - 1.0)},
        }
    return site, calibration, tref, rows, data["aeronet_datetime"][used]


def date_ranges(times):
    """The first and last match, and each UTC day with its number of matches, as header lines."""
    if len(times) == 0:
        return ["no matches used"]
    times = np.sort(times.astype("datetime64[s]"))
    days, counts = np.unique(times.astype("datetime64[D]"), return_counts=True)
    return [f"{times[0]} to {times[-1]} UTC, {len(times)} matches",
            "days: " + ", ".join(f"{day} ({n})" for day, n in zip(days, counts))]


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--site", nargs=2, action="append", required=True, metavar=("MATCHED", "COEFFS"),
                   help="a matched pickle and its tempcorr_<site>.txt; repeat for each site")
    p.add_argument("-o", "--output", required=True, help="the V0 file to write")
    args = p.parse_args()

    sites = [site_v0(matched, coeffs) for matched, coeffs in args.site]
    trefs = {tref for _site, _cal, tref, _rows, _times in sites}
    if len(trefs) > 1:
        sys.exit(f"the sites' temperature corrections have different TREFs: {sorted(trefs)}")
    tref = trefs.pop()

    table = [f"# SeaSTAR V0 transferred from AERONET (transfer_v0.py), {DARK}, temperature corrected with",
             f"# each site's {METHOD} {ORDER == 2 and 'quadratic' or 'linear'} coefficients, at TREF {tref:g} C, 1 AU.",
             "# origin: V0 = b*V0_aeronet; intercept: V0 = a + b*V0_aeronet. +- are statistical standard errors",
             "# from the line fits only. extrap is V0_aeronet over the largest matched AERONET voltage, how far",
             "# the line is extrapolated. rms is the fractional scatter about the line."]
    table.append("# AERONET calibrations, and the matches the fits used (by any channel):")
    for site, calibration, _tref, _rows, times in sites:
        table.append(f"#   {site}: {calibration}")
        table += [f"#     {line}" for line in date_ranges(times)]
    table.append(f"# {'site':16s} {'ch':>4s} {'nm':>5s} {'AERONET':9s} {'n':>4s} {'V0_aeronet':>12s} {'extrap':>6s}"
                 f" {'origin b':>11s} {'V0 origin':>20s} {'rms':>7s}"
                 f" {'intercept a':>12s} {'b':>11s} {'V0 intercept':>20s} {'rms':>7s}")
    params = [f"V0_SEASTAR_TREF={tref:g}"]
    channels = sorted({ch for _s, _c, _t, rows, _d in sites for ch in rows})
    for ch in channels:
        for site, _cal, _t, rows, _d in sites:
            if ch not in rows:
                continue
            r = rows[ch]
            o, i = r["origin"], r["intercept"]
            table.append(f"# {site:16s} {'ch' + str(ch):>4s} {r['wl']:5d} {r['v_stem'].replace('V*_', ''):9s} {r['n']:4d}"
                         f" {r['V0_aeronet']:12.1f} {r['extrapolation']:5.2f}x"
                         f" {o['b']:11.4e} {o['V0']:9.4f} ± {o['err']:.1e} {o['rms']:7.4f}"
                         f" {i['a']:+12.4f} {i['b']:11.4e} {i['V0']:9.4f} ± {i['err']:.1e} {i['rms']:7.4f}")
            site_tag = re.sub(r"[^A-Z0-9]+", "_", site.upper())
            for fit in FITS:
                params.append(f"V0_SEASTAR_{site_tag}_{fit.upper()}_CH{ch}={r[fit]['V0']:.6e}")
            params.append(f"V0_SEASTAR_{site_tag}_INTERCEPT_A_CH{ch}={i['a']:.6e}")
        for fit in FITS:
            values = np.array([rows[ch][fit]["V0"] for _s, _c, _t, rows, _d in sites if ch in rows])
            errs = np.array([rows[ch][fit]["err"] for _s, _c, _t, rows, _d in sites if ch in rows])
            w = 1.0 / errs ** 2
            mean, err = np.sum(w * values) / np.sum(w), 1.0 / np.sqrt(np.sum(w))
            spread = (values.max() - values.min()) / mean * 100
            table.append(f"# {'weighted mean':16s} {'ch' + str(ch):>4s} {fit:9s} V0 {mean:.4f} ± {err:.1e}"
                         f"   sites differ by {spread:.2f}%")
            params.append(f"V0_SEASTAR_{fit.upper()}_CH{ch}={mean:.6e}")
        a = np.array([rows[ch]["intercept"]["a"] for _s, _c, _t, rows, _d in sites if ch in rows])
        w = 1.0 / np.array([rows[ch]["intercept"]["a_err"] for _s, _c, _t, rows, _d in sites if ch in rows]) ** 2
        a_mean, a_err = np.sum(w * a) / np.sum(w), 1.0 / np.sqrt(np.sum(w))
        table.append(f"# {'weighted mean':16s} {'ch' + str(ch):>4s} {'intercept':9s} a  {a_mean:+.4f} ± {a_err:.1e}")
        params.append(f"V0_SEASTAR_INTERCEPT_A_CH{ch}={a_mean:.6e}")

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text("\n".join(table) + "\n\n" + "\n".join(params) + "\n")
    print("\n".join(table))
    print(f"wrote {args.output}")


if __name__ == "__main__":
    main()
