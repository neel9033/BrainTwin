"""
Step 1 - Load every input file and print sanity checks.

Reads:  both midthickness meshes, the resting-state fMRI, the Schaefer atlas,
        and the head-motion summary.
Writes: data/derived/<subject>/<run>/load_check.json (the numbers printed below).

Run:    python pipeline/step1_load_check.py                    (default run, full check)
        python pipeline/step1_load_check.py --run rfMRI_REST2_LR --files-only
                                       (another run: files exist + fMRI header matches)
"""

import json
import sys

import config  # first: stops early with a clear message if the wrong Python is used

import nibabel as nib
import numpy as np

from brain_io import get_cortex_columns, load_atlas, load_fmri, load_mesh, parse_region_name


def check_meshes(raw_paths):
    """
    Load the left and right meshes and print their sizes and coordinate ranges.
    Input: raw_paths dict from config.get_raw_paths().
    Output: dict of results per hemisphere.
    """
    print("\n=== 1. Surface meshes (midthickness, MNINonLinear) ===")
    results = {}
    for hemisphere in ("L", "R"):
        brain_points, triangles = load_mesh(raw_paths[f"mesh_{hemisphere}"])
        triangles_valid = bool(triangles.min() >= 0 and triangles.max() < len(brain_points))
        print(f"  {hemisphere}: {len(brain_points):,} vertices, {len(triangles):,} triangles, "
              f"triangle indices valid: {triangles_valid}")
        for axis_index, axis_name in enumerate("xyz"):
            low, high = brain_points[:, axis_index].min(), brain_points[:, axis_index].max()
            print(f"      {axis_name} range: {low:7.1f} to {high:6.1f} mm")
        results[hemisphere] = {
            "n_vertices": int(len(brain_points)),
            "n_triangles": int(len(triangles)),
            "triangle_indices_valid": triangles_valid,
            "x_range_mm": [float(brain_points[:, 0].min()), float(brain_points[:, 0].max())],
        }
    return results


def check_fmri(raw_paths):
    """
    Load the fMRI time series and print its shape, timing, and structure counts.
    Input: raw_paths dict.
    Output: (results dict, fmri_data, brain_model_axis) so later checks can reuse them.
    """
    print("\n=== 2. Resting-state fMRI ===")
    fmri_data, brain_model_axis, series_axis = load_fmri(raw_paths["fmri"])
    n_timepoints, n_grayordinates = fmri_data.shape
    print(f"  shape (timepoints x grayordinates): {n_timepoints:,} x {n_grayordinates:,}")
    print(f"  timepoints: {n_timepoints}  "
          f"(header step = {series_axis.step} {series_axis.unit}; HCP-YA true TR = {config.TR_SECONDS} s "
          f"-> {n_timepoints * config.TR_SECONDS / 60:.1f} min scan)")

    n_cortex_columns = 0
    results = {"n_timepoints": int(n_timepoints), "n_grayordinates": int(n_grayordinates)}
    for hemisphere in ("L", "R"):
        column_indices, vertex_indices = get_cortex_columns(brain_model_axis, hemisphere)
        n_cortex_columns += len(column_indices)
        print(f"  cortex {hemisphere}: {len(column_indices):,} vertices with data "
              f"(out of {config.VERTICES_PER_HEMISPHERE:,}; medial wall removed)")
        results[f"cortex_{hemisphere}_vertices"] = int(len(column_indices))
    n_subcortical = n_grayordinates - n_cortex_columns
    print(f"  subcortical voxels: {n_subcortical:,} (not used yet)")
    results["subcortical_voxels"] = int(n_subcortical)

    # Data quality: any missing values or flat (zero-variance) cortex signals?
    cortex_data = fmri_data[:, :n_cortex_columns]
    n_nan = int(np.isnan(cortex_data).sum())
    n_flat = int((cortex_data.std(axis=0) == 0).sum())
    print(f"  cortex NaN values: {n_nan}, flat (zero-variance) vertices: {n_flat}")
    results["cortex_nan_values"] = n_nan
    results["cortex_flat_vertices"] = n_flat
    return results, brain_model_axis


def check_atlas():
    """
    Load the Schaefer atlas and print how many regions and labelled vertices it has.
    Input: none (path comes from config).
    Output: (results dict, vertex_labels, label_table).
    """
    print("\n=== 3. Schaefer 2018 atlas (200 parcels, 7 networks) ===")
    vertex_labels, label_table = load_atlas(config.ATLAS_DLABEL, config.VERTICES_PER_HEMISPHERE)
    print(f"  regions in label table: {len(label_table)}")

    results = {"n_regions": len(label_table)}
    for hemisphere in ("L", "R"):
        labels = vertex_labels[hemisphere]
        region_ids = np.unique(labels[labels > 0])
        n_labelled = int((labels > 0).sum())
        print(f"  {hemisphere}: {len(region_ids)} regions (ids {region_ids.min()}-{region_ids.max()}), "
              f"{n_labelled:,} labelled vertices, {int((labels == 0).sum()):,} unlabelled (medial wall)")
        results[f"{hemisphere}_regions"] = int(len(region_ids))
        results[f"{hemisphere}_labelled_vertices"] = n_labelled

    # Count regions per network and make sure the name hemisphere agrees with the surface it is on
    network_counts = {}
    hemisphere_mismatches = 0
    for region_id, full_name in label_table.items():
        parts = parse_region_name(full_name)
        network_counts[parts["network"]] = network_counts.get(parts["network"], 0) + 1
        if not np.any(vertex_labels[parts["hemisphere"]] == region_id):
            hemisphere_mismatches += 1
    print(f"  regions per network: {network_counts}")
    print(f"  regions whose name hemisphere doesn't match their surface: {hemisphere_mismatches}")
    results["regions_per_network"] = network_counts
    results["hemisphere_name_mismatches"] = hemisphere_mismatches
    return results, vertex_labels, label_table


def check_matching(brain_model_axis, vertex_labels, label_table):
    """
    Match fMRI cortex columns to atlas labels BY VERTEX INDEX and count overlap.
    Inputs: fMRI brain_model_axis, vertex_labels and label_table from the atlas.
    Output: dict of match counts.
    """
    print("\n=== 4. fMRI <-> atlas vertex matching (by vertex index) ===")
    results = {}
    regions_with_data = set()
    for hemisphere in ("L", "R"):
        _column_indices, fmri_vertices = get_cortex_columns(brain_model_axis, hemisphere)
        atlas_labels = vertex_labels[hemisphere]
        labels_at_fmri_vertices = atlas_labels[fmri_vertices]

        fmri_with_region = int((labels_at_fmri_vertices > 0).sum())
        fmri_without_region = int((labels_at_fmri_vertices == 0).sum())
        atlas_vertex_set = set(np.flatnonzero(atlas_labels > 0))
        atlas_without_fmri = len(atlas_vertex_set - set(fmri_vertices.tolist()))
        regions_with_data.update(np.unique(labels_at_fmri_vertices[labels_at_fmri_vertices > 0]).tolist())

        print(f"  {hemisphere}: fMRI vertices {len(fmri_vertices):,} | "
              f"with an atlas region {fmri_with_region:,} | "
              f"in fMRI but unlabelled {fmri_without_region:,} | "
              f"labelled but missing from fMRI {atlas_without_fmri:,}")
        results[hemisphere] = {
            "fmri_vertices": int(len(fmri_vertices)),
            "fmri_vertices_with_region": fmri_with_region,
            "fmri_vertices_unlabelled": fmri_without_region,
            "atlas_vertices_missing_from_fmri": atlas_without_fmri,
        }

    missing_regions = sorted(set(label_table) - regions_with_data)
    print(f"  regions with at least one fMRI vertex: {len(regions_with_data)} / {len(label_table)}")
    if missing_regions:
        print(f"  WARNING - regions with no fMRI data: {missing_regions}")
    results["regions_with_fmri_data"] = len(regions_with_data)
    results["regions_missing_fmri"] = missing_regions
    return results


def check_motion(raw_paths):
    """
    Read the mean relative head motion for this run (a QC number).
    Input: raw_paths dict. Output: mean relative RMS motion in mm (float).
    """
    print("\n=== 5. Head motion (QC) ===")
    mean_motion_mm = float(np.loadtxt(raw_paths["motion"]))
    verdict = "low" if mean_motion_mm < 0.15 else "check - above 0.15 mm"
    print(f"  mean relative RMS motion: {mean_motion_mm:.4f} mm ({verdict})")
    return mean_motion_mm


def check_files_only(raw_paths, run_name):
    """
    Quick check for an extra run: the files exist, and the fMRI header has the
    same layout as the default run (reads only the header, not the 400 MB of data).
    Inputs: raw_paths for the run, run_name. Output: dict of results.
    """
    print("\n=== fMRI header (data not loaded) ===")
    fmri_header = nib.load(str(raw_paths["fmri"])).header
    series_axis, brain_model_axis = fmri_header.get_axis(0), fmri_header.get_axis(1)
    results = {"n_timepoints": len(series_axis), "n_grayordinates": len(brain_model_axis)}
    print(f"  shape (timepoints x grayordinates): {len(series_axis):,} x {len(brain_model_axis):,}")

    reference_paths = config.get_raw_paths(run_name=config.RUN_NAME)
    reference_axis = nib.load(str(reference_paths["fmri"])).header.get_axis(1)
    for hemisphere in ("L", "R"):
        _columns, vertices = get_cortex_columns(brain_model_axis, hemisphere)
        _columns, reference_vertices = get_cortex_columns(reference_axis, hemisphere)
        same = np.array_equal(vertices, reference_vertices)
        print(f"  cortex {hemisphere}: {len(vertices):,} vertices; same vertices as {config.RUN_NAME}: {same}")
        results[f"cortex_{hemisphere}_same_as_default_run"] = bool(same)
    return results


def main():
    """
    Run every check for the chosen subject and run, print the results,
    and save them to load_check.json. With --files-only, just check that the
    run's files exist and its fMRI header matches the default run.
    """
    run_name = config.get_run_name()
    files_only = "--files-only" in sys.argv
    raw_paths = config.get_raw_paths(run_name=run_name)
    print(f"Subject: {config.SUBJECT_ID} (HCP {config.get_hcp_id()}), run: {run_name}")
    for name, path in raw_paths.items():
        print(f"  {name:7s} {'OK     ' if path.exists() else 'MISSING'} {path}")
    print(f"  atlas   {'OK     ' if config.ATLAS_DLABEL.exists() else 'MISSING'} {config.ATLAS_DLABEL}")
    if not all(path.exists() for path in raw_paths.values()):
        sys.exit("Some files are missing - see MISSING above.")

    if files_only:
        summary = {
            "subject_id": config.SUBJECT_ID,
            "hcp_id": config.get_hcp_id(),
            "run_name": run_name,
            "files_only": True,
            "fmri_header": check_files_only(raw_paths, run_name),
            "mean_relative_motion_mm": check_motion(raw_paths),
        }
        output_path = config.get_derived_dir(run_name=run_name) / "load_check.json"
        output_path.write_text(json.dumps(summary, indent=2))
        print(f"\nSaved {output_path.relative_to(config.REPO_DIR)}")
        return

    mesh_results = check_meshes(raw_paths)
    fmri_results, brain_model_axis = check_fmri(raw_paths)
    atlas_results, vertex_labels, label_table = check_atlas()
    match_results = check_matching(brain_model_axis, vertex_labels, label_table)
    mean_motion_mm = check_motion(raw_paths)

    # Mesh vertex count must equal the CIFTI per-hemisphere vertex count,
    # otherwise "mesh vertex index = CIFTI vertex index" would not hold.
    print("\n=== 6. Mesh <-> CIFTI vertex count ===")
    for hemisphere in ("L", "R"):
        same = mesh_results[hemisphere]["n_vertices"] == config.VERTICES_PER_HEMISPHERE
        print(f"  {hemisphere}: mesh {mesh_results[hemisphere]['n_vertices']:,} vs CIFTI "
              f"{config.VERTICES_PER_HEMISPHERE:,} -> {'match' if same else 'MISMATCH'}")

    summary = {
        "subject_id": config.SUBJECT_ID,
        "hcp_id": config.get_hcp_id(),
        "run_name": run_name,
        "meshes": mesh_results,
        "fmri": fmri_results,
        "atlas": atlas_results,
        "matching": match_results,
        "mean_relative_motion_mm": mean_motion_mm,
    }
    output_path = config.get_derived_dir(run_name=run_name) / "load_check.json"
    output_path.write_text(json.dumps(summary, indent=2))
    print(f"\nSaved {output_path.relative_to(config.REPO_DIR)}")


if __name__ == "__main__":
    main()
