#!/usr/bin/env python3
"""Fit SeaSTAR temperature-correction coefficients from AERONET <-> SeaSTAR matches.

Reads a matched pickle written by match_aeronet_seastar.py (one AERONET site) and, for each
SeaSTAR channel and the AERONET wavelength it is matched to, fits how the SeaSTAR voltage
departs from AERONET's (temperature-corrected) voltage against the SeaSTAR channel temperature.
The coefficients have AERONET's form, so the correction would be applied as

    Vcorr = V / (1 + A*dT)                 linear
    Vcorr = V / (1 + A*dT + B*dT^2)        quadratic,      dT = T - TREF

AERONET is treated as the truth, and the correction acts on the SeaSTAR voltage. Three methods:
  ratio       y = |V_seastar| / V_aeronet is fitted with a polynomial p0 + p1*dT (+ p2*dT^2),
              giving A = p1/p0 and B = p2/p0
  residual    AERONET is regressed on the temperature-corrected SeaSTAR voltage, with the
              correction fitted at the same time, by least squares on the fractional residuals
              (V_aeronet - model) / V_aeronet:
                  V_aeronet = a + b * |V_seastar| / (1 + A*dT + B*dT^2)
              the ratio method is this with a = 0. the plotted y is |V_seastar| over the SeaSTAR
              voltage the regression expects from V_aeronet, b*|V_seastar| / (V_aeronet - a)
  scatter     A (and B) are chosen to minimise the scatter of the corrected SeaSTAR voltage about a
              straight line fitted against V_aeronet, std(Vcorr / (a + b*V_aeronet) - 1), with a and b
              refitted for every trial (the rms shown on plot_response.py's plots). it starts from
              the residual method's coefficients. no standard errors are estimated. the plotted y is
              |V_seastar| / (a + b*V_aeronet), with the straight line of the corrected voltages
Each is done for both dark-subtracted SeaSTAR voltages (darksub_lin and darksub_quad).

Nothing is applied to the L0.6 data. Output, in --outdir and --plotdir:
  - tempcorr_<site>.txt: a table of every fit, and parameters.sh-style lines
        TEMPCORR_<SITE>_<METHOD>_<DARK>_<ORDER>_A_CH<n>   (and _B_ for the quadratic)
    ch10 (1020 nm) is matched to both AERONET 1020 detectors: the lines use the Si one, and the
    InGaAs fits are in the table.
  - tempcorr_<site>_<method>.png: y (the ratio normalised by p0, or the residual or scatter
    method's y from the quadratic fit) against channel temperature for each channel, darksub_quad voltages,
    coloured by day, with both fits' 1 + A*dT (+ B*dT^2) drawn.
"""

import argparse
import pickle
import re
import sys
from pathlib import Path

import numpy as np
from scipy.optimize import least_squares, minimize
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from match_aeronet_seastar import triplet_field
from plot_matched import matched_pairs, pair_label, source_day, style_panel, DAY_COLOURS

METHODS = ("ratio", "residual", "scatter")
DARKS = ("darksub_lin", "darksub_quad")
ORDERS = {1: "LIN", 2: "QUAD"}
PLOT_DARK = "darksub_quad"
FIT_COLOURS = {1: "#52514e", 2: "#c2185b"}


def pair_data(data, ch, wl, v_stem, dark):
    """|SeaSTAR| dark-subtracted mean, AERONET triplet mean, SeaSTAR temperature, and which rows have all three."""
    seastar = np.abs(data[f"seastar_ch{ch}_{wl}nm_{dark}_mean"])
    aeronet = data[triplet_field(v_stem, "mean")]
    temp = data[f"seastar_ch{ch}_{wl}nm_temp_mean"]
    ok = ((data[f"seastar_ch{ch}_{wl}nm_n_used"] > 0) & np.isfinite(seastar) & np.isfinite(aeronet)
          & (aeronet > 0) & np.isfinite(temp) & (temp != 0.0))  # 0 is the temperature sensors' startup value
    return seastar, aeronet, temp, ok


def ratio_fit(seastar, aeronet, dT, order):
    """Fit y = |V_seastar| / V_aeronet = p0 + p1*dT (+ p2*dT^2).
    Returns y, and a dict with p (normalised to p0 = 1), A, B, their standard errors, and the rms."""
    y = seastar / aeronet
    p, cov = np.polyfit(dT, y, order, cov=True)
    p, err = p[::-1], np.sqrt(np.diag(cov))[::-1]  # p0, p1, (p2)
    model = np.polynomial.polynomial.polyval(dT, p)
    return y / p[0], {"p": p / p[0], "A": p[1] / p[0], "A_err": err[1] / p[0],
                      "B": p[2] / p[0] if order == 2 else 0.0, "B_err": err[2] / p[0] if order == 2 else 0.0,
                      "rms": np.std(y / model - 1.0)}


def residual_fit(seastar, aeronet, dT, order):
    """Fit V_aeronet = a + b * |V_seastar| / (1 + A*dT (+ B*dT^2)) by least squares on the fractional residuals.
    Returns y = b*|V_seastar| / (V_aeronet - a), and a dict with p = (1, A, B), A, B, their standard errors,
    a, b, and the rms of the fractional residuals."""
    def residuals(x):
        a, b, *coeffs = x
        return (a + b * seastar / np.polynomial.polynomial.polyval(dT, [1.0, *coeffs]) - aeronet) / aeronet
    b0, a0 = np.polyfit(seastar, aeronet, 1)  # start from the uncorrected regression
    result = least_squares(residuals, [a0, b0] + [0.0] * order, x_scale="jac")
    a, b, *coeffs = result.x
    # standard errors from the jacobian, scaled by the residual variance
    dof = len(aeronet) - len(result.x)
    cov = np.linalg.pinv(result.jac.T @ result.jac) * np.sum(result.fun ** 2) / dof
    err = np.sqrt(np.diag(cov))
    return b * seastar / (aeronet - a), {"p": np.array([1.0, *coeffs]), "A": coeffs[0], "A_err": err[2],
                                         "B": coeffs[1] if order == 2 else 0.0, "B_err": err[3] if order == 2 else 0.0,
                                         "a": a, "b": b, "rms": np.std(result.fun)}


def line_scatter(corrected, aeronet):
    """The straight line of corrected |V_seastar| against V_aeronet, as (a, b), and the fractional scatter about it."""
    b, a = np.polyfit(aeronet, corrected, 1)
    return a, b, np.std(corrected / (a + b * aeronet) - 1.0)


def scatter_fit(seastar, aeronet, dT, order):
    """Choose A (and B) to minimise the scatter of Vcorr = |V_seastar| / (1 + A*dT (+ B*dT^2)) about a straight
    line against V_aeronet, refitting the line for each trial. Starts from the residual method's coefficients.
    Returns y = |V_seastar| / (a + b*V_aeronet) and a dict like residual_fit's, with NaN standard errors."""
    def scatter(coeffs):
        return line_scatter(seastar / np.polynomial.polynomial.polyval(dT, [1.0, *coeffs]), aeronet)[2]
    start = residual_fit(seastar, aeronet, dT, order)[1]["p"][1:]
    result = minimize(scatter, start, method="Nelder-Mead",
                      options={"xatol": 1e-9, "fatol": 1e-11, "maxiter": 4000})
    coeffs = result.x
    a, b, rms = line_scatter(seastar / np.polynomial.polynomial.polyval(dT, [1.0, *coeffs]), aeronet)
    return seastar / (a + b * aeronet), {"p": np.array([1.0, *coeffs]), "A": coeffs[0], "A_err": np.nan,
                                         "B": coeffs[1] if order == 2 else 0.0, "B_err": np.nan,
                                         "a": a, "b": b, "rms": rms}


METHOD_FITS = {"ratio": ratio_fit, "residual": residual_fit, "scatter": scatter_fit}


def uncorrected_rms(method, seastar, aeronet):
    """The scatter with no temperature correction, as a fraction: of the ratio about its mean, of the
    fractional residuals about the straight-line regression of V_aeronet on |V_seastar| (residual), or of
    |V_seastar| about its straight line against V_aeronet (scatter)."""
    if method == "ratio":
        y = seastar / aeronet
        return np.std(y / np.mean(y) - 1.0)
    if method == "scatter":
        return line_scatter(seastar, aeronet)[2]
    b, a = np.polyfit(seastar, aeronet, 1)
    return np.std((a + b * seastar - aeronet) / aeronet)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("matched", help="matched pickle written by match_aeronet_seastar.py")
    p.add_argument("--tref", type=float, default=30.0, help="reference temperature, in °C (default 30)")
    p.add_argument("--min-points", type=int, default=10, help="fewest matches a channel is fitted with (default 10)")
    p.add_argument("--outdir", required=True, help="directory for the coefficient file")
    p.add_argument("--plotdir", required=True, help="directory for the plots")
    args = p.parse_args()

    with open(args.matched, "rb") as fh:
        matched = pickle.load(fh)
    data, metadata = matched["data"], matched["metadata"]
    site = metadata.get("aeronet_site") or Path(args.matched).stem.replace("matched_", "")
    site_tag = re.sub(r"[^A-Z0-9]+", "_", site.upper())
    pairs = matched_pairs(metadata["channel_wavelengths"])
    days = np.array([source_day(s) for s in data["seastar_source"]])

    table = [f"# temperature-correction fits, {site}, from {Path(args.matched).name} (fit_tempcorr.py)",
             f"# Vcorr = V / (1 + A*dT + B*dT^2), dT = T - {args.tref:g} C, AERONET taken as true. +- are standard",
             "# errors (none for scatter). rms is the fractional scatter about the fit (ratio: of the ratio;",
             "# residual: of V_aeronet; scatter: of |V_seastar| about its straight line against V_aeronet),",
             "# rms0 the same with no temperature correction",
             f"# {'pair':42s} {'method':8s} {'dark':12s} {'n':>4s} {'T range C':>11s} {'rms0':>7s}"
             f" {'lin A':>22s} {'rms':>7s} {'quad A':>22s} {'quad B':>22s} {'rms':>7s}"]
    params = [f"TEMPCORR_TREF={args.tref:g}"]
    results = {}  # (method, pair) -> {order: fit} for the plotted dark variant
    for v_index, (ch, wl, v_stem) in enumerate(pairs):
        primary = v_stem == matched_pairs({ch: wl})[0][2]  # the first AERONET stem for this wavelength
        for method in METHODS:
            for dark in DARKS:
                seastar, aeronet, temp, ok = pair_data(data, ch, wl, v_stem, dark)
                label = pair_label(ch, wl, v_stem)
                if ok.sum() < args.min_points:
                    table.append(f"# {label:42s} {method:8s} {dark:12s} {ok.sum():4d} too few matches, not fitted")
                    continue
                dT = temp[ok] - args.tref
                method_fit = METHOD_FITS[method]
                ys, fits = {}, {}
                for order in ORDERS:
                    ys[order], fits[order] = method_fit(seastar[ok], aeronet[ok], dT, order)
                y = ys[2]  # plotted: for the residual and scatter methods, y depends on the quadratic fit's a and b
                rms0 = uncorrected_rms(method, seastar[ok], aeronet[ok])
                lin, quad = fits[1], fits[2]
                table.append(f"# {label:42s} {method:8s} {dark:12s} {ok.sum():4d} {temp[ok].min():5.1f}-{temp[ok].max():5.1f}"
                             f" {rms0:7.4f} {lin['A']:+.3e} ± {lin['A_err']:.1e} {lin['rms']:7.4f}"
                             f" {quad['A']:+.3e} ± {quad['A_err']:.1e} {quad['B']:+.3e} ± {quad['B_err']:.1e} {quad['rms']:7.4f}")
                if primary:
                    for order, name in ORDERS.items():
                        stem = f"TEMPCORR_{site_tag}_{method.upper()}_{dark.upper()}_{name}"
                        params.append(f"{stem}_A_CH{ch}={fits[order]['A']:.6e}")
                        if order == 2:
                            params.append(f"{stem}_B_CH{ch}={fits[order]['B']:.6e}")
                if dark == PLOT_DARK:
                    results[(method, (ch, wl, v_stem))] = (fits, y, temp[ok], days[ok])

    Path(args.outdir).mkdir(parents=True, exist_ok=True)
    path = Path(args.outdir) / f"tempcorr_{site}.txt"
    path.write_text("\n".join(table) + "\n\n" + "\n".join(params) + "\n")
    print(f"wrote {path}")

    Path(args.plotdir).mkdir(parents=True, exist_ok=True)
    day_list = sorted(set(days) - {""})
    for method in METHODS:
        fitted = [pair for pair in pairs if (method, pair) in results]
        columns = 4
        rows = (len(fitted) + columns - 1) // columns
        fig, axes = plt.subplots(rows, columns, figsize=(4.2 * columns, 3.2 * rows + 1.2), squeeze=False)
        for ax in axes.flat[len(fitted):]:
            ax.set_visible(False)
        for ax, pair in zip(axes.flat, fitted):
            fits, y, temp, pair_days = results[(method, pair)]
            for day, colour in zip(day_list, DAY_COLOURS * 2):
                sel = pair_days == day
                if sel.any():
                    ax.scatter(temp[sel], y[sel], s=14, color=colour, label=day,
                               edgecolors="white", linewidths=0.5)
            t = np.linspace(temp.min(), temp.max(), 100)
            for order, f in fits.items():
                ax.plot(t, np.polynomial.polynomial.polyval(t - args.tref, f["p"]), color=FIT_COLOURS[order],
                        linewidth=1.2, label=f"{ORDERS[order].lower()}")
            ax.text(0.03, 0.04, f"lin A {fits[1]['A']:+.2e}\nquad A {fits[2]['A']:+.2e} B {fits[2]['B']:+.1e}",
                    transform=ax.transAxes, fontsize=7.5, va="bottom")
            ax.set_title(pair_label(*pair), loc="left", fontsize=9)
            ax.set_xlabel("SeaSTAR channel temperature (°C)")
            ax.set_ylabel({"ratio": "ratio / p0", "residual": "|V| / expected |V|",
                           "scatter": "|V| / straight line"}[method])
            style_panel(ax)
        handles, labels = axes.flat[0].get_legend_handles_labels()
        fig.legend(handles, labels, loc="upper center", bbox_to_anchor=(0.5, 0.975), ncol=len(labels),
                   frameon=False, fontsize=9)
        what = {"ratio": "|V_SeaSTAR| / V_AERONET",
                "residual": "|V_SeaSTAR| / SeaSTAR voltage expected from V_AERONET = a + b|V|/(1+A dT+B dT²)",
                "scatter": "|V_SeaSTAR| / straight line of corrected |V_SeaSTAR| against V_AERONET"}[method]
        fig.suptitle(f"{site}: {what} against temperature ({PLOT_DARK}, TREF {args.tref:g} °C)", y=0.995)
        fig.tight_layout(rect=(0, 0, 1, 0.95))
        plot_path = Path(args.plotdir) / f"tempcorr_{site}_{method}.png"
        fig.savefig(plot_path, dpi=110)
        plt.close(fig)
        print(f"  plot: {plot_path}")


if __name__ == "__main__":
    main()
