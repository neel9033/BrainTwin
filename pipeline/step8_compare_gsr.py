"""
Step 8 - Does global signal regression (GSR) help? Compare the results for the
same subject without and with it.

The global signal is the brain-wide average fMRI signal. It carries breathing,
heart-rate and arousal fluctuations that lift every region at once, which makes
every correlation look stronger. GSR removes it (step 2; on by default). This step
puts the two versions next to each other so we can decide which to use.

Reads:  for each run in config.RUNS_TO_COMPARE, data/derived/<subject>/<run>/ and
        <run>_gsr/ (steps 2, 3, 5 run once with --no-gsr and once with GSR), plus
        run_comparison.json and run_comparison_gsr.json (step 7, both ways).
Writes: data/derived/<subject>/gsr_comparison.json          all numbers printed below
        data/derived/<subject>/gsr_comparison_heatmaps.png   default run, without vs with GSR
        data/derived/<subject>/gsr_comparison_values.png     distribution of every connection's r

Run:    python pipeline/step8_compare_gsr.py
"""

import config  # first: stops early with a clear message if the wrong Python is used

import json
import sys

import matplotlib

matplotlib.use("Agg")  # draw to files only, no window
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from step7_compare_runs import plot_matrix_pair, short_run_name, upper_triangle

N_TOP = 10
VERSIONS = {False: "without GSR", True: "with GSR"}
# Line colors for the distribution plot (validated categorical pair: blue, orange)
VERSION_COLORS = {False: "#2a78d6", True: "#eb6834"}


def missing_input_message(path, gsr):
    """
    Explain which commands produce a missing input file.
    Inputs: the missing Path, gsr (which version is missing). Output: message string.
    """
    python = config.BRAINTWIN_PYTHON
    flag = "--gsr" if gsr else "--no-gsr"
    return (f"Missing {path.relative_to(config.REPO_DIR)}. Run the {VERSIONS[gsr]} version first:\n"
            + "".join(f"  {python} pipeline/{step} --run {run} {flag}\n"
                      for run in config.RUNS_TO_COMPARE
                      for step in ("step2_parcellate.py", "step3_connectivity.py", "step5_graph_stats.py"))
            + f"  {python} pipeline/step7_compare_runs.py {flag}")


def load_version(run_name, gsr):
    """
    Load one run's step 2-5 outputs, without or with GSR.
    Inputs: run_name, gsr (True/False). Output: dict with connectivity,
            region_stats, summary, and gsr_info (None without GSR).
    """
    folder = config.get_derived_dir(run_name=run_name, gsr=gsr)
    summary_path = folder / "graph_summary.json"
    if not summary_path.exists():
        sys.exit(missing_input_message(summary_path, gsr))
    gsr_info_path = folder / "gsr_info.json"
    return {
        "connectivity": np.load(folder / "connectivity.npy"),
        "region_stats": pd.read_csv(folder / "region_stats.csv"),
        "summary": json.loads(summary_path.read_text()),
        "gsr_info": json.loads(gsr_info_path.read_text()) if gsr else None,
    }


def load_reproducibility(gsr):
    """
    Load step 7's REST1-vs-REST2 comparison, without or with GSR.
    Input: gsr (True/False). Output: comparison dict.
    """
    path = config.get_subject_dir() / f"run_comparison{config.get_variant_suffix(gsr)}.json"
    if not path.exists():
        sys.exit(missing_input_message(path, gsr))
    return json.loads(path.read_text())


def matrix_numbers(matrix, networks):
    """
    Summarize one connectivity matrix.
    Inputs: 200 x 200 correlation matrix, network name per region (array).
    Output: dict with mean r, share of negative pairs, and mean r within vs
            between networks (a bigger gap = sharper network blocks).
    """
    values = upper_triangle(matrix)
    same_network = upper_triangle(networks[:, None] == networks[None, :])
    within, between = values[same_network].mean(), values[~same_network].mean()
    return {
        "mean_r": float(values.mean()),
        "share_negative": float((values < 0).mean()),
        "mean_r_within_network": float(within),
        "mean_r_between_network": float(between),
        "within_minus_between": float(within - between),
    }


def top_by_strength(region_stats, n_top=N_TOP):
    """
    The n_top strongest regions (hubs) in the thresholded graph.
    Inputs: region_stats table, how many. Output: list of dicts (id, name, network).
    """
    top = region_stats.sort_values("strength", ascending=False).head(n_top)
    return [{"id": int(row.id), "name": f"{row.hemisphere}H {row.region_name}", "network": row.network}
            for row in top.itertuples()]


def compare_versions(runs_data, reproducibility, regions):
    """
    Compute every without-vs-with-GSR number.
    Inputs: runs_data {run_name: {False: version, True: version}},
            reproducibility {False: step 7 dict, True: step 7 dict}, regions table.
    Output: comparison dict for JSON.
    """
    networks = regions["network"].to_numpy()
    per_run = {}
    for run_name, versions in runs_data.items():
        run_result = {}
        for gsr, data in versions.items():
            summary = data["summary"]
            run_result[VERSIONS[gsr]] = {
                **matrix_numbers(data["connectivity"], networks),
                "modularity": summary["modularity_schaefer_networks"],
                "average_clustering": summary["average_clustering"],
                "graph_cutoff_r": summary["threshold"]["weakest_kept_r"],
                "isolated_regions": len(summary["isolated_regions"]),
                "fraction_edges_within_network": summary["fraction_edges_within_network"],
                "top_strength": top_by_strength(data["region_stats"]),
            }
        # How similar the two versions are, connection by connection and hub by hub
        without, with_gsr = versions[False], versions[True]
        top_ids = [{region["id"] for region in run_result[VERSIONS[gsr]]["top_strength"]} for gsr in (False, True)]
        run_result["matrix_similarity_r"] = float(np.corrcoef(
            upper_triangle(without["connectivity"]), upper_triangle(with_gsr["connectivity"]))[0, 1])
        run_result["top_strength_shared"] = len(top_ids[0] & top_ids[1])
        run_result["gsr_variance_explained_mean"] = with_gsr["gsr_info"]["variance_explained_mean"]
        run_result["gsr_variance_explained_by_network"] = with_gsr["gsr_info"]["variance_explained_by_network"]
        per_run[short_run_name(run_name)] = run_result

    return {
        "subject_id": config.SUBJECT_ID,
        "hcp_id": config.get_hcp_id(),
        "runs": list(runs_data),
        "global_signal": runs_data[config.RUN_NAME][True]["gsr_info"]["global_signal"],
        "per_run": per_run,
        "reproducibility": {
            VERSIONS[gsr]: {
                "matrix_correlation": comparison["matrix_correlation"],
                "strength_correlation": comparison["strength_correlation"],
                "top10_edge_overlap": comparison["top10_edge_overlap"],
            }
            for gsr, comparison in reproducibility.items()
        },
    }


def plot_value_distribution(matrices, run_label, output_path):
    """
    Histogram of every region pair's r, without vs with GSR, on one axis.
    Inputs: {False: matrix, True: matrix}, run label for the title, PNG path.
    Output: none (writes PNG).
    """
    bin_edges = np.arange(-0.8, 1.0001, 0.02)
    figure, axes = plt.subplots(figsize=(8, 4.2), dpi=150)
    figure.patch.set_facecolor("#fcfcfb")
    axes.set_facecolor("#fcfcfb")
    axes.axvline(0, color="#b5b4ad", linewidth=1, zorder=1)
    centers = (bin_edges[:-1] + bin_edges[1:]) / 2
    # The curve further left gets its label on its left side, the other on its right
    leftmost = min(matrices, key=lambda gsr: upper_triangle(matrices[gsr]).mean())
    highest_count = 0
    for gsr, matrix in matrices.items():
        values = upper_triangle(matrix)
        counts, _edges = np.histogram(values, bins=bin_edges)
        highest_count = max(highest_count, counts.max())
        axes.plot(centers, counts, color=VERSION_COLORS[gsr], linewidth=2, zorder=3)
        axes.fill_between(centers, counts, color=VERSION_COLORS[gsr], alpha=0.12, linewidth=0, zorder=2)
        # Direct label beside the peak, in text ink (the line beside it carries the color)
        peak = int(np.argmax(counts))
        on_left = gsr == leftmost
        axes.annotate(f"{VERSIONS[gsr]}\nmean r {values.mean():.2f}, {(values < 0).mean():.0%} negative",
                      xy=(centers[peak], counts[peak]), xytext=(-12 if on_left else 12, 0),
                      textcoords="offset points", ha="right" if on_left else "left", va="bottom",
                      fontsize=8, color="#2b2b29")
    axes.set_xlim(bin_edges[0], bin_edges[-1])
    axes.set_ylim(0, highest_count * 1.18)
    axes.set_xlabel("Pearson r between two regions", fontsize=8, color="#5f5f5b")
    axes.set_ylabel("number of region pairs", fontsize=8, color="#5f5f5b")
    axes.tick_params(labelsize=7, colors="#5f5f5b", length=0)
    axes.grid(axis="y", color="#e8e7e3", linewidth=0.8)
    axes.set_axisbelow(True)
    for spine in axes.spines.values():
        spine.set_visible(False)
    handles = [plt.Line2D([], [], color=VERSION_COLORS[gsr], linewidth=2) for gsr in matrices]
    axes.legend(handles, [VERSIONS[gsr] for gsr in matrices], frameon=False, fontsize=8, loc="upper right")
    axes.set_title(f"Every connection's strength, {run_label} — {config.SUBJECT_ID}", fontsize=11,
                   color="#2b2b29", weight="bold", loc="left")
    figure.savefig(output_path, facecolor=figure.get_facecolor(), bbox_inches="tight")
    plt.close(figure)


def print_summary(comparison):
    """
    Print the comparison as readable tables.
    Input: comparison dict. Output: none.
    """
    labels = list(VERSIONS.values())
    print(f"Global signal: {comparison['global_signal']}\n")
    rows = [
        ("mean r (all pairs)", "mean_r", "{:.3f}"),
        ("share of negative pairs", "share_negative", "{:.0%}"),
        ("mean r within networks", "mean_r_within_network", "{:.3f}"),
        ("mean r between networks", "mean_r_between_network", "{:.3f}"),
        ("within minus between", "within_minus_between", "{:.3f}"),
        ("modularity (Schaefer)", "modularity", "{:.3f}"),
        ("graph edges within network", "fraction_edges_within_network", "{:.0%}"),
        ("average clustering", "average_clustering", "{:.3f}"),
        ("weakest r kept in 10% graph", "graph_cutoff_r", "{:.3f}"),
        ("isolated regions", "isolated_regions", "{}"),
    ]
    for run_label, result in comparison["per_run"].items():
        print(f"--- {run_label} ---  (global signal explained {result['gsr_variance_explained_mean']:.0%} "
              f"of a region's signal on average)")
        print(f"  {'':30s} {labels[0]:>12s} {labels[1]:>12s}")
        for title, key, number_format in rows:
            values = [number_format.format(result[label][key]) for label in labels]
            print(f"  {title:30s} {values[0]:>12s} {values[1]:>12s}")
        print(f"  without vs with GSR, connection by connection: r = {result['matrix_similarity_r']:.2f}")
        print(f"  top-{N_TOP} hubs by strength shared by both versions: {result['top_strength_shared']} of {N_TOP}\n")

    print("--- Reproducibility: REST1 vs REST2 (same person, two days) ---")
    print(f"  {'':30s} {labels[0]:>12s} {labels[1]:>12s}")
    for title, key in [("whole-matrix agreement r", "matrix_correlation"),
                       ("region strength agreement r", "strength_correlation"),
                       ("top-10% edges in both scans", "top10_edge_overlap")]:
        values = [comparison["reproducibility"][label][key] for label in labels]
        number_format = "{:.0%}" if key == "top10_edge_overlap" else "{:.3f}"
        print(f"  {title:30s} {number_format.format(values[0]):>12s} {number_format.format(values[1]):>12s}")

    default_label = short_run_name(config.RUN_NAME)
    result = comparison["per_run"][default_label]
    print(f"\n--- Top {N_TOP} hubs by strength, {default_label} ---")
    print(f"  {'rank':>4}  {labels[0]:34s} {labels[1]:34s}")
    for rank, (first, second) in enumerate(zip(result[labels[0]]["top_strength"],
                                               result[labels[1]]["top_strength"]), start=1):
        print(f"  {rank:>4}  {first['name'] + ' (' + first['network'] + ')':34s} "
              f"{second['name'] + ' (' + second['network'] + ')':34s}")


def main():
    """
    Load both versions of every run, compare them, print the results,
    and save the JSON and both figures.
    """
    runs_data = {run_name: {gsr: load_version(run_name, gsr) for gsr in (False, True)}
                 for run_name in config.RUNS_TO_COMPARE}
    reproducibility = {gsr: load_reproducibility(gsr) for gsr in (False, True)}
    regions = pd.read_csv(config.get_derived_dir(gsr=False) / "regions.csv")

    comparison = compare_versions(runs_data, reproducibility, regions)
    print_summary(comparison)

    output_dir = config.get_subject_dir()
    default_label = short_run_name(config.RUN_NAME)
    default_versions = runs_data[config.RUN_NAME]
    (output_dir / "gsr_comparison.json").write_text(json.dumps(comparison, indent=2))
    plot_matrix_pair(
        [default_versions[False]["connectivity"], default_versions[True]["connectivity"]],
        [f"{default_label}  ·  {VERSIONS[False]}", f"{default_label}  ·  {VERSIONS[True]}"],
        regions,
        f"Global signal regression — {config.SUBJECT_ID}  ·  same scan, before and after",
        output_dir / "gsr_comparison_heatmaps.png",
    )
    plot_value_distribution({gsr: data["connectivity"] for gsr, data in default_versions.items()},
                            default_label, output_dir / "gsr_comparison_values.png")
    print()
    for file_name in ["gsr_comparison.json", "gsr_comparison_heatmaps.png", "gsr_comparison_values.png"]:
        print(f"Saved {(output_dir / file_name).relative_to(config.REPO_DIR)}")


if __name__ == "__main__":
    main()
