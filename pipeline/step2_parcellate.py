"""
Step 2 - Average the fMRI signal inside each brain region.

Reads:  the resting-state fMRI and the Schaefer atlas (paths from config).
Writes: data/derived/<subject>/<run>/region_timeseries.npy  (timepoints x 200, float32)
        data/derived/<subject>/<run>/regions.csv            (one row per region)
        With global signal regression (the default, config.USE_GSR) these go in
        <run>_gsr/ instead, plus global_signal.npy (timepoints) and gsr_info.json
        (how much it explained). With --no-gsr they go in <run>/.

Column i of region_timeseries.npy is the region in row i of regions.csv
(region ids 1..200 in order, so column i = region id i+1).

Run:    python pipeline/step2_parcellate.py                    (default run)
        python pipeline/step2_parcellate.py --run rfMRI_REST2_LR (another run)
        python pipeline/step2_parcellate.py --no-gsr             (keep the global signal)
"""

import json

import config  # first: stops early with a clear message if the wrong Python is used

import numpy as np
import pandas as pd

from brain_io import get_cortex_columns, load_atlas, load_fmri, parse_region_name


def load_region_colors(atlas_info_path):
    """
    Read the official Schaefer region colors from the atlas info text file.
    Input: path to *_info.txt (alternating lines: name, then "id R G B A").
    Output: dict {region_id: "#rrggbb"}.
    """
    lines = atlas_info_path.read_text().strip().splitlines()
    region_colors = {}
    for value_line in lines[1::2]:
        region_id, red, green, blue, _alpha = (int(value) for value in value_line.split())
        region_colors[region_id] = f"#{red:02x}{green:02x}{blue:02x}"
    return region_colors


def parcellate(fmri_data, brain_model_axis, vertex_labels, region_ids):
    """
    Average the fMRI time series over all vertices in each region.
    Inputs: fmri_data (timepoints x grayordinates), brain_model_axis of the fMRI,
            vertex_labels {"L": (32492,), "R": (32492,)} from the atlas,
            region_ids: sorted list of region ids to compute.
    Output: (region_timeseries, vertex_counts)
            region_timeseries: float32 array (timepoints x n_regions)
            vertex_counts: dict {region_id: number of vertices averaged}
    """
    # Gather, for both hemispheres, every fMRI column and the region it belongs to.
    # The lookup goes column -> vertex index -> atlas label (never by column position).
    all_columns, all_labels = [], []
    for hemisphere in ("L", "R"):
        column_indices, vertex_indices = get_cortex_columns(brain_model_axis, hemisphere)
        all_columns.append(column_indices)
        all_labels.append(vertex_labels[hemisphere][vertex_indices])
    all_columns = np.concatenate(all_columns)
    all_labels = np.concatenate(all_labels)

    n_timepoints = fmri_data.shape[0]
    region_timeseries = np.zeros((n_timepoints, len(region_ids)), dtype=np.float32)
    vertex_counts = {}
    for position, region_id in enumerate(region_ids):
        region_columns = all_columns[all_labels == region_id]
        region_timeseries[:, position] = fmri_data[:, region_columns].mean(axis=1)
        vertex_counts[region_id] = int(len(region_columns))
    return region_timeseries, vertex_counts


def regress_global_signal(fmri_data, region_timeseries):
    """
    Global signal regression: remove the brain-wide average signal from each region.
    The global signal is the mean over all grayordinates (cortex + subcortex) at
    each timepoint. For each region we fit  region = a + b * global_signal  and keep
    what is left over. (Doing this on region averages gives exactly the same result
    as doing it on every vertex and then averaging, because fitting is linear.)
    Inputs: fmri_data (timepoints x grayordinates),
            region_timeseries (timepoints x regions).
    Output: (cleaned_timeseries float32 (timepoints x regions, each region now has mean 0),
             global_signal float32 (timepoints,),
             variance_explained float array (regions,): share of each region's
             variance the global signal accounted for, 0..1)
    """
    global_signal = fmri_data.mean(axis=1, dtype=np.float64)
    design = np.column_stack([np.ones_like(global_signal), global_signal])
    region_values = region_timeseries.astype(np.float64)
    coefficients, *_ = np.linalg.lstsq(design, region_values, rcond=None)
    cleaned = region_values - design @ coefficients
    variance_explained = 1 - cleaned.var(axis=0) / region_values.var(axis=0)
    return cleaned.astype(np.float32), global_signal.astype(np.float32), variance_explained


def build_region_table(label_table, vertex_counts, region_colors):
    """
    Make the regions.csv table.
    Inputs: label_table {id: full name}, vertex_counts {id: count},
            region_colors {id: hex color}.
    Output: pandas DataFrame with columns
            id, full_name, region_name, hemisphere, network, vertex_count, color
    """
    rows = []
    for region_id in sorted(label_table):
        name_parts = parse_region_name(label_table[region_id])
        rows.append({
            "id": region_id,
            "full_name": label_table[region_id],
            "region_name": name_parts["region_name"],
            "hemisphere": name_parts["hemisphere"],
            "network": name_parts["network"],
            "vertex_count": vertex_counts[region_id],
            "color": region_colors[region_id],
        })
    return pd.DataFrame(rows)


def main():
    """
    Parcellate the chosen subject/run (--run) and save the region time series
    and region table. Prints a few checks along the way.
    """
    run_name = config.get_run_name()
    use_gsr = config.get_use_gsr()
    raw_paths = config.get_raw_paths(run_name=run_name)
    output_dir = config.get_derived_dir(run_name=run_name, gsr=use_gsr)

    print(f"Loading fMRI: {raw_paths['fmri'].name}")
    fmri_data, brain_model_axis, _series_axis = load_fmri(raw_paths["fmri"])
    vertex_labels, label_table = load_atlas(config.ATLAS_DLABEL, config.VERTICES_PER_HEMISPHERE)
    region_colors = load_region_colors(config.ATLAS_INFO_TXT)
    region_ids = sorted(label_table)

    region_timeseries, vertex_counts = parcellate(fmri_data, brain_model_axis, vertex_labels, region_ids)
    regions = build_region_table(label_table, vertex_counts, region_colors)

    if use_gsr:
        region_timeseries, global_signal, variance_explained = regress_global_signal(
            fmri_data, region_timeseries)
        gsr_info = {
            "global_signal": "mean of all grayordinates (cortex + subcortex) per timepoint",
            "regressors": ["constant", "global signal"],
            "variance_explained_mean": float(variance_explained.mean()),
            "variance_explained_min": float(variance_explained.min()),
            "variance_explained_max": float(variance_explained.max()),
            "variance_explained_by_network": {
                network: float(variance_explained[(regions["network"] == network).to_numpy()].mean())
                for network in config.NETWORK_ORDER
            },
        }
        print("Global signal regression ON")
        print(f"  global signal explained {gsr_info['variance_explained_mean']:.0%} of a region's "
              f"signal on average (range {gsr_info['variance_explained_min']:.0%} to "
              f"{gsr_info['variance_explained_max']:.0%})")
        for network, share in gsr_info["variance_explained_by_network"].items():
            print(f"    {network:12s} {share:.0%}")
        np.save(output_dir / "global_signal.npy", global_signal)
        (output_dir / "gsr_info.json").write_text(json.dumps(gsr_info, indent=2))

    # Checks
    counts = regions["vertex_count"]
    print(f"\nregion_timeseries shape: {region_timeseries.shape} (timepoints x regions)")
    print(f"vertices per region: min {counts.min()}, median {int(counts.median())}, max {counts.max()}")
    print(f"total vertices averaged: {counts.sum():,} (step 1 said 29,301 + 29,308 = 58,609)")
    print(f"NaN values: {int(np.isnan(region_timeseries).sum())}, "
          f"flat regions: {int((region_timeseries.std(axis=0) == 0).sum())}")
    print("\nregions per hemisphere x network:")
    print(regions.pivot_table(index="network", columns="hemisphere", values="id",
                              aggfunc="count", sort=False).to_string())
    print("\nfirst 3 rows of regions.csv:")
    print(regions.head(3).to_string(index=False))

    np.save(output_dir / "region_timeseries.npy", region_timeseries)
    regions.to_csv(output_dir / "regions.csv", index=False)
    print(f"\nSaved {(output_dir / 'region_timeseries.npy').relative_to(config.REPO_DIR)}")
    print(f"Saved {(output_dir / 'regions.csv').relative_to(config.REPO_DIR)}")


if __name__ == "__main__":
    main()
