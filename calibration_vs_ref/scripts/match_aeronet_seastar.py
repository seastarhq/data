#!/usr/bin/env python3
"""Match AERONET sun observations against SeaSTAR L0.6 photometer voltages.

Input:
  - AERONET pickle (output of read_aeronet.py): {"data": structured_array,
    "metadata": {...}} with sun observations and per-wavelength voltages/AOD.
  - One or more SeaSTAR L0.6 files (.L06), each loadable via
    np.load(allow_pickle=True) with keys 'array_data' and 'metadata'.
  - For each L0.6: a sibling channel_wavelengths.sh in the campaign's
    L0.6/setup/ folder, defining CH1_NM..CH5_NM (blank = unmapped).

Output:
  - Pickled {"data": structured_array, "metadata": {...}} of paired rows:
    one row per AERONET observation in the date range, with windowed mean
    and std of each mapped SeaSTAR channel.
  - Per-channel scatter plots (unless --no-plots).
"""

import argparse
import glob
import os
import pickle
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np


SEASTAR_CHANNELS = ["ch1_1x", "ch2_1x", "ch3_1x", "ch4_1x", "ch5_1x"]
SEASTAR_CHANNEL_NUMS = [1, 2, 3, 4, 5]

VALID_FLAG_FIELDS = {
    "tracking_flags", "robot_flags", "housekeeping_flags",
    "radiometer_1x_flags", "radiometer_100x_flags", "radiometer_10kx_flags",
    "cloud_flags",
}

# AERONET wavelengths the script knows how to look up. Keys here are the
# wavelength values from channel_wavelengths.sh; values are the (V_field_stem,
# AOD_field) tuples. 1020 maps to BOTH Si and InGaAs columns.
AERONET_WAVELENGTH_LOOKUP = {
    340:  [("V*_340",         "AOD_340")],
    380:  [("V*_380",         "AOD_380")],
    440:  [("V*_440",         "AOD_440")],
    500:  [("V*_500",         "AOD_500")],
    675:  [("V*_675",         "AOD_675")],
    870:  [("V*_870",         "AOD_870")],
    935:  [("V*_935",         None)],          # AERONET reports water vapor here, no AOD
    1020: [("V*_1020",        "AOD_1020"),
           ("V*_1020_InGaAs", "AOD_1020_InGaAs")],
    1640: [("V*_1640",        "AOD_1640")],
}


def parse_iso_utc(s):
    if s is None or s == "":
        return None
    s = s.strip()
    # Accept "Z" suffix or "+00:00"; fall back to naive-UTC interpretation.
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
    except ValueError as e:
        raise argparse.ArgumentTypeError(f"invalid ISO timestamp {s!r}: {e}")
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return np.datetime64(dt.astimezone(timezone.utc).replace(tzinfo=None), "ms")


def parse_channel_wavelengths(path):
    """Read a channel_wavelengths.sh and return {channel_num: wavelength_nm}.

    Channels with blank values are omitted from the dict.
    """
    mapping = {}
    pattern = re.compile(r"^\s*CH([1-5])_NM\s*=\s*([^#\s]*)\s*(#.*)?$")
    with open(path) as fh:
        for line in fh:
            m = pattern.match(line)
            if not m:
                continue
            ch = int(m.group(1))
            val = m.group(2).strip()
            if val == "":
                continue
            try:
                mapping[ch] = int(val)
            except ValueError:
                raise ValueError(
                    f"{path}: CH{ch}_NM={val!r} is not an integer wavelength"
                )
    return mapping


def find_channel_wavelengths_file(l06_path):
    """Walk up from a .L06 file's path to find sibling L0.6/setup/channel_wavelengths.sh."""
    p = Path(l06_path).resolve()
    for parent in [p.parent, *p.parents]:
        candidate = parent / "L0.6" / "setup" / "channel_wavelengths.sh"
        if candidate.is_file():
            return candidate
        candidate = parent / "setup" / "channel_wavelengths.sh"
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(
        f"Could not locate channel_wavelengths.sh near {l06_path}"
    )


def load_l06(path):
    """Load a SeaSTAR .L06 file. Returns (array_data, metadata)."""
    npz = np.load(path, allow_pickle=True)
    return npz["array_data"], npz["metadata"][()]


def load_aeronet(path):
    with open(path, "rb") as fh:
        return pickle.load(fh)


def build_output_dtype(channel_map):
    """channel_map: list of (ch_num, wavelength_nm, source_label) tuples."""
    fields = [
        ("aeronet_datetime", "datetime64[ms]"),
        ("aeronet_jday", "f8"),
        ("aeronet_obs_type", "U4"),
        ("aeronet_level", "U6"),
        ("aeronet_zenith", "f8"),
        ("aeronet_airmass", "f8"),
        ("aeronet_alpha", "f8"),
        ("aeronet_water_vapor", "f8"),
        # Carry full AERONET V/AOD payload through (one row per match)
        ("aeronet_aod_missing_flags", "i4"),
    ]
    # AERONET V*_<wl> and AOD_<wl> for the wavelengths actually mapped:
    aeronet_fields_added = set()
    for ch_num, wl, _src in channel_map:
        for v_stem, aod_field in AERONET_WAVELENGTH_LOOKUP[wl]:
            for vn in (1, 2, 3):
                f = v_stem.replace("*", str(vn))
                if f not in aeronet_fields_added:
                    fields.append((f"aeronet_{f}", "f8"))
                    aeronet_fields_added.add(f)
            if aod_field and aod_field not in aeronet_fields_added:
                fields.append((f"aeronet_{aod_field}", "f8"))
                aeronet_fields_added.add(aod_field)

    # SeaSTAR channel statistics
    for ch_num, wl, src in channel_map:
        suffix = f"ch{ch_num}_{wl}nm"
        fields += [
            (f"seastar_{suffix}_mean", "f8"),
            (f"seastar_{suffix}_std", "f8"),
            (f"seastar_{suffix}_n_used", "i4"),
            (f"seastar_{suffix}_n_total", "i4"),
        ]

    fields.append(("seastar_source", "U64"))
    return np.dtype(fields), aeronet_fields_added


def build_drop_mask(l06, drop_fields):
    """Boolean mask: True = row should be DROPPED."""
    mask = np.zeros(len(l06), dtype=bool)
    for f in drop_fields:
        mask |= (l06[f] != 0)
    return mask


def match_window(aeronet_dt_ns, l06_dt_ns, half_width_ns):
    """Return (lo, hi) indices into a sorted l06_dt_ns covering [t-W, t+W]."""
    lo = np.searchsorted(l06_dt_ns, aeronet_dt_ns - half_width_ns, side="left")
    hi = np.searchsorted(l06_dt_ns, aeronet_dt_ns + half_width_ns, side="right")
    return lo, hi


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--aeronet-pickle", required=True,
                   help="Path to the AERONET pickle (output of read_aeronet.py).")
    p.add_argument("--seastar-l06", action="append", required=True,
                   help="Path to a SeaSTAR .L06 file. Repeatable.")
    p.add_argument("--start", type=parse_iso_utc, default=None,
                   help="UTC start (ISO 8601), inclusive. Default: full overlap.")
    p.add_argument("--end", type=parse_iso_utc, default=None,
                   help="UTC end (ISO 8601), exclusive. Default: full overlap.")
    p.add_argument("--window-seconds", type=float, default=30.0,
                   help="Half-width of L0.6 averaging window in seconds (default: 30).")
    p.add_argument("--drop-on-flags", default="cloud_flags,tracking_flags",
                   help=("Comma-separated L0.6 flag fields; rows with any non-zero "
                         "value in these fields are excluded from averaging."))
    p.add_argument("-o", "--output", required=True,
                   help="Output pickle path.")
    p.add_argument("--plots-dir", default=None,
                   help="Directory for diagnostic scatter plots.")
    p.add_argument("--no-plots", action="store_true",
                   help="Skip plot generation.")
    args = p.parse_args()

    drop_fields = [f.strip() for f in args.drop_on_flags.split(",") if f.strip()]
    bad = [f for f in drop_fields if f not in VALID_FLAG_FIELDS]
    if bad:
        sys.exit(f"unknown flag field(s): {bad}. Valid: {sorted(VALID_FLAG_FIELDS)}")

    # 1. Load AERONET.
    aeronet = load_aeronet(args.aeronet_pickle)
    aeronet_data = aeronet["data"]
    aeronet_meta = aeronet["metadata"]
    if aeronet_meta.get("filters_applied", {}).get("type") not in ("sun", "both"):
        print(f"warning: AERONET pickle filtered to type="
              f"{aeronet_meta.get('filters_applied',{}).get('type')!r}; expected 'sun' "
              f"for calibration. Continuing anyway.", file=sys.stderr)

    # 2. Load each L0.6 + its channel map; concatenate all into one big block.
    l06_blocks = []
    channel_map_per_block = []
    sources = []
    for l06_path in args.seastar_l06:
        arr, meta = load_l06(l06_path)
        cw_path = find_channel_wavelengths_file(l06_path)
        ch_map = parse_channel_wavelengths(cw_path)
        if not ch_map:
            print(f"warning: no channels mapped in {cw_path}; skipping {l06_path}",
                  file=sys.stderr)
            continue
        unknown_wl = [(c, w) for c, w in ch_map.items()
                      if w not in AERONET_WAVELENGTH_LOOKUP]
        if unknown_wl:
            sys.exit(f"{cw_path}: wavelengths {unknown_wl} have no AERONET match. "
                     f"Valid: {sorted(AERONET_WAVELENGTH_LOOKUP)}")
        l06_blocks.append(arr)
        channel_map_per_block.append((l06_path, ch_map))
        sources.append(os.path.basename(l06_path))

    if not l06_blocks:
        sys.exit("No usable L0.6 inputs after channel-mapping check.")

    # 3. Validate the channel mapping is consistent across L0.6 files (the
    #    output dtype is built from one mapping; differing maps are a foot-gun).
    canonical_map = channel_map_per_block[0][1]
    for path, m in channel_map_per_block[1:]:
        if m != canonical_map:
            sys.exit(f"Channel mapping in {path} differs from "
                     f"{channel_map_per_block[0][0]}: {m} vs {canonical_map}. "
                     f"All inputs must use the same mapping.")

    # 4. Concatenate L0.6 data, sort by datetime.
    l06 = np.concatenate(l06_blocks)
    sort_idx = np.argsort(l06["datetime"])
    l06 = l06[sort_idx]
    # Track per-row source for the seastar_source field
    src_array = np.concatenate([
        np.full(len(b), os.path.basename(p), dtype="U64")
        for b, (p, _m) in zip(l06_blocks, channel_map_per_block)
    ])
    src_array = src_array[sort_idx]

    # 5. Determine effective date range.
    aeronet_t = aeronet_data["aeronet_datetime"] if "aeronet_datetime" in aeronet_data.dtype.names else aeronet_data["datetime"]
    l06_t = l06["datetime"]
    t_start = max(aeronet_t.min(), l06_t.min()) if args.start is None else args.start
    t_end_max = min(aeronet_t.max(), l06_t.max()) + np.timedelta64(1, "ms")
    t_end = t_end_max if args.end is None else args.end
    if t_end <= t_start:
        sys.exit(f"Effective date range is empty: start={t_start}, end={t_end}. "
                 f"AERONET span: {aeronet_t.min()}..{aeronet_t.max()}; "
                 f"L0.6 span: {l06_t.min()}..{l06_t.max()}. "
                 f"Check timezone of L0.6 datetimes.")
    # Sanity-check overlap
    if (l06_t.max() < aeronet_t.min()) or (l06_t.min() > aeronet_t.max()):
        sys.exit(f"AERONET and L0.6 time ranges do not overlap. "
                 f"AERONET: {aeronet_t.min()}..{aeronet_t.max()}; "
                 f"L0.6: {l06_t.min()}..{l06_t.max()}. "
                 f"Likely a timezone mismatch.")

    # 6. Filter AERONET to the date range and build the output array.
    mask = (aeronet_t >= t_start) & (aeronet_t < t_end)
    a = aeronet_data[mask]
    print(f"AERONET rows in [{t_start}, {t_end}): {len(a)}", file=sys.stderr)

    channel_map_list = sorted(canonical_map.items())  # [(ch_num, wl), ...]
    # Resolve label for each entry; ch_map_full has (ch_num, wl, src_label)
    ch_map_full = [(ch, wl, f"ch{ch}_{wl}nm") for ch, wl in channel_map_list]

    out_dtype, aeronet_fields_added = build_output_dtype(ch_map_full)
    out = np.empty(len(a), dtype=out_dtype)

    # 7. Pre-compute drop mask on L0.6.
    drop_mask = build_drop_mask(l06, drop_fields)
    l06_t_ns = l06_t.astype("datetime64[ns]").astype(np.int64)
    half_width_ns = int(args.window_seconds * 1e9)

    # 8. Per-row windowed averaging.
    for i, row in enumerate(a):
        aeronet_dt_ns = np.datetime64(row["datetime"], "ns").astype(np.int64)
        out[i]["aeronet_datetime"] = row["datetime"]
        out[i]["aeronet_jday"] = row["jday"]
        out[i]["aeronet_obs_type"] = row["obs_type"]
        out[i]["aeronet_level"] = row["level"]
        out[i]["aeronet_zenith"] = row["zenith"]
        out[i]["aeronet_airmass"] = row["airmass"]
        out[i]["aeronet_alpha"] = row["alpha"]
        out[i]["aeronet_water_vapor"] = row["water_vapor"]
        out[i]["aeronet_aod_missing_flags"] = row["aod_missing_flags"]

        for f in aeronet_fields_added:
            out[i][f"aeronet_{f}"] = row[f]

        lo, hi = match_window(aeronet_dt_ns, l06_t_ns, half_width_ns)
        n_total = hi - lo
        keep = ~drop_mask[lo:hi]
        n_used = int(keep.sum())
        for ch_num, wl, src_label in ch_map_full:
            field = f"ch{ch_num}_1x"
            suffix = f"ch{ch_num}_{wl}nm"
            if n_used == 0:
                out[i][f"seastar_{suffix}_mean"] = np.nan
                out[i][f"seastar_{suffix}_std"] = np.nan
            else:
                vals = l06[field][lo:hi][keep]
                out[i][f"seastar_{suffix}_mean"] = np.nanmean(vals)
                out[i][f"seastar_{suffix}_std"] = np.nanstd(vals)
            out[i][f"seastar_{suffix}_n_used"] = n_used
            out[i][f"seastar_{suffix}_n_total"] = n_total

        if n_total > 0:
            out[i]["seastar_source"] = src_array[lo]
        else:
            out[i]["seastar_source"] = ""

    # 9. Metadata + write.
    metadata = {
        "aeronet_pickle": os.path.abspath(args.aeronet_pickle),
        "seastar_l06_files": [os.path.abspath(p) for p in args.seastar_l06],
        "channel_wavelengths": canonical_map,
        "window_seconds": args.window_seconds,
        "drop_on_flags": drop_fields,
        "date_range_utc": [str(t_start), str(t_end)],
        "n_matches": int(len(out)),
        "n_with_l06_samples": int(np.sum(out[f"seastar_ch{ch_map_full[0][0]}_{ch_map_full[0][1]}nm_n_used"] > 0)),
        "aeronet_calibration": aeronet_meta.get("calibration"),
        "aeronet_filters_applied": aeronet_meta.get("filters_applied"),
    }

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "wb") as fh:
        pickle.dump({"data": out, "metadata": metadata}, fh, protocol=pickle.HIGHEST_PROTOCOL)

    print(f"wrote {args.output}: {len(out)} matched rows, "
          f"{metadata['n_with_l06_samples']} with at least one usable L0.6 sample.")

    # 10. Plots.
    if args.plots_dir and not args.no_plots:
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
        except ImportError:
            print("matplotlib not available; skipping plots.", file=sys.stderr)
            return
        Path(args.plots_dir).mkdir(parents=True, exist_ok=True)
        for ch_num, wl, src_label in ch_map_full:
            for v_stem, aod_field in AERONET_WAVELENGTH_LOOKUP[wl]:
                # Use V1 as the AERONET voltage (V1/V2/V3 are the triplet)
                v_field = f"aeronet_{v_stem.replace('*', '1')}"
                ch_mean = out[f"seastar_{src_label}_mean"]
                v_aer = out[v_field]
                airmass = out["aeronet_airmass"]
                ok = np.isfinite(ch_mean) & np.isfinite(v_aer) & np.isfinite(airmass)
                if not ok.any():
                    continue
                fig, ax = plt.subplots(figsize=(6, 5))
                sc = ax.scatter(v_aer[ok], ch_mean[ok], c=airmass[ok], s=20)
                ax.set_xlabel(f"AERONET {v_stem.replace('*','1')}")
                ax.set_ylabel(f"SeaSTAR ch{ch_num} mean (counts)")
                ax.set_title(f"ch{ch_num} ({wl} nm) vs AERONET {v_stem}")
                cb = fig.colorbar(sc, ax=ax)
                cb.set_label("airmass")
                fig.tight_layout()
                tag = v_stem.replace("*_", "").replace("(", "").replace(")", "")
                fname = Path(args.plots_dir) / f"ch{ch_num}_{wl}nm_vs_{tag}.png"
                fig.savefig(fname, dpi=110)
                plt.close(fig)
                print(f"  plot: {fname}")


if __name__ == "__main__":
    main()
