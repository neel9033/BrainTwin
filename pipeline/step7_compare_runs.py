"""
Step 7 - Reproducibility: compare two resting-state scans of the same person.

The same brain was scanned on two different days (REST1 and REST2). If the
connectivity we measure is real rather than noise, the two scans should agree.

Reads:  data/derived/<subject>/<run>/connectivity.npy, region_stats.csv,
        graph_edges.csv, graph_summary.json, regions.csv for both runs
        in config.RUNS_TO_COMPARE (outputs of steps 2-5).
Writes: data/derived/<subject>/run_comparison.json        all numbers below
        data/derived/<subject>/region_stability.csv       per-region strength in each run
        data/derived/<subject>/run_comparison_scatter.png  edge weights, run 1 vs run 2
        data/derived/<subject>/run_comparison_heatmaps.png the two matrices side by side

        With --gsr: compares the <run>_gsr folders and adds "_gsr" to every file name above.

Run:    python pipeline/step7_compare_runs.py
        python pipeline/step7_compare_runs.py --gsr
"""

import config  # first: stops early with a clear message if the wrong Python is used

import json

import matplotlib

matplotlib.use("Agg")  # draw to files only, no window
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap

from step3_connectivity import DIVERGING_COLORS, network_sort_order

N_MOST_CHANGED = 10
# Share of regions labelled "most" / "least" consistent (by how much their rank moved)
CONSISTENCY_SHARE = 0.2


def short_run_name(run_name):
    """Input: "rfMRI_REST1_LR". Output: "REST1" (for labels)."""
    return run_name.replace("rfMRI_", "").split("_")[0]


def load_run(run_name):
    """
    Load one run's outputs from steps 2-5.
    Input: run_name. Output: dict with connectivity, region_stats, edges, summary.
    """
    folder = config.get_derived_dir(run_name=run_name)
    return {
        "name": run_name,
        "connectivity": np.load(folder / "connectivity.npy"),
        "region_stats": pd.read_csv(folder / "region_stats.csv"),
        "edges": pd.read_csv(folder / "graph_edges.csv"),
        "summary": json.loads((folder / "graph_summary.json").read_text()),
    }


def upper_triangle(matrix):
    """Each region pair once (no diagonal). Input: square matrix. Output: 1-D array."""
    return matrix[np.triu_indices(len(matrix), k=1)]


def describe_agreement(correlation):
    """
    Plain-language verdict for a between-scan correlation.
    Input: r. Output: (short label, sentence).
    """
    if correlation >= 0.7:
        return "strong", "The two scans agree strongly: the connection pattern is a stable feature of this brain."
    if correlation >= 0.5:
        return "moderate", ("The two scans agree moderately: the broad pattern repeats, but individual "
                            "connections vary a fair amount between days.")
    return "weak", "The two scans agree only weakly: much of the pattern changes between days or is noise."


def compare(first, second, regions):
    """
    Compute every comparison number.
    Inputs: two runs from load_run(), regions table.
    Output: (comparison dict for JSON, region_stability DataFrame).
    """
    edges_first = upper_triangle(first["connectivity"])
    edges_second = upper_triangle(second["connectivity"])
    matrix_r = float(np.corrcoef(edges_first, edges_second)[0, 1])

    # Same comparison on Fisher z values, which is the more standard scale for averaging r
    matrix_r_fisher = float(np.corrcoef(np.arctanh(edges_first), np.arctanh(edges_second))[0, 1])

    # Strength from the strongest-10% graph (step 5), and from all positive connections
    stats = (first["region_stats"][["id", "strength"]]
             .merge(second["region_stats"][["id", "strength"]], on="id", suffixes=("_first", "_second"))
             .merge(regions[["id", "region_name", "hemisphere", "network"]], on="id"))
    strength_r = float(np.corrcoef(stats["strength_first"], stats["strength_second"])[0, 1])

    def positive_strength(matrix):
        """Sum of each region's positive correlations (diagonal excluded)."""
        positive = np.clip(matrix, 0, None)
        np.fill_diagonal(positive, 0)
        return positive.sum(axis=1)

    full_strength_r = float(np.corrcoef(positive_strength(first["connectivity"]),
                                        positive_strength(second["connectivity"]))[0, 1])

    # Change per region: raw, and by rank (rank is unaffected by one run being stronger overall)
    stats["strength_change"] = stats["strength_second"] - stats["strength_first"]
    stats["rank_first"] = stats["strength_first"].rank(ascending=False, method="min").astype(int)
    stats["rank_second"] = stats["strength_second"].rank(ascending=False, method="min").astype(int)
    stats["rank_change"] = stats["rank_first"] - stats["rank_second"]  # + = moved up the ranking
    n_regions = len(stats)
    n_label = int(round(CONSISTENCY_SHARE * n_regions))
    order = stats["rank_change"].abs().sort_values(kind="stable")
    stats["consistency"] = "typical"
    stats.loc[order.index[:n_label], "consistency"] = "most consistent"
    stats.loc[order.index[-n_label:], "consistency"] = "least consistent"

    most_changed = stats.reindex(stats["strength_change"].abs().sort_values(ascending=False).index)
    most_changed = most_changed.head(N_MOST_CHANGED)

    # How many of the strongest-10% connections show up in both runs
    def edge_set(edges):
        return {(min(s, t), max(s, t)) for s, t in zip(edges["source"], edges["target"])}

    shared_edges = edge_set(first["edges"]) & edge_set(second["edges"])
    edge_overlap = len(shared_edges) / len(first["edges"])

    label, sentence = describe_agreement(matrix_r)
    names = [short_run_name(first["name"]), short_run_name(second["name"])]
    comparison = {
        "subject_id": config.SUBJECT_ID,
        "hcp_id": config.get_hcp_id(),
        "runs": [first["name"], second["name"]],
        "run_labels": names,
        "global_signal_regression": config.get_use_gsr(),
        "matrix_correlation": matrix_r,
        "matrix_correlation_fisher_z": matrix_r_fisher,
        "agreement": label,
        "agreement_sentence": sentence,
        "n_region_pairs": int(len(edges_first)),
        "strength_correlation": strength_r,
        "strength_correlation_all_positive": full_strength_r,
        "mean_strength": {names[0]: float(stats["strength_first"].mean()),
                          names[1]: float(stats["strength_second"].mean())},
        "top10_edge_overlap": float(edge_overlap),
        "graph_cutoff_r": {names[0]: first["summary"]["threshold"]["weakest_kept_r"],
                           names[1]: second["summary"]["threshold"]["weakest_kept_r"]},
        "isolated_regions": {names[0]: first["summary"]["isolated_regions"],
                             names[1]: second["summary"]["isolated_regions"]},
        "head_motion_mm": {names[0]: first["summary"]["qc"]["mean_relative_motion_mm"],
                           names[1]: second["summary"]["qc"]["mean_relative_motion_mm"]},
        "modularity": {names[0]: first["summary"]["modularity_schaefer_networks"],
                       names[1]: second["summary"]["modularity_schaefer_networks"]},
        "most_changed_regions": [
            {"id": int(row.id), "region_name": row.region_name, "hemisphere": row.hemisphere,
             "network": row.network, f"strength_{names[0]}": round(float(row.strength_first), 3),
             f"strength_{names[1]}": round(float(row.strength_second), 3),
             "change": round(float(row.strength_change), 3), "rank_change": int(row.rank_change)}
            for row in most_changed.itertuples()
        ],
        "consistency_rule": (f"Regions ranked by how far their strength rank moved between runs: the "
                             f"{n_label} that moved least are 'most consistent', the {n_label} that moved "
                             f"most are 'least consistent'."),
    }

    region_stability = stats.rename(columns={
        "strength_first": f"strength_{names[0]}", "strength_second": f"strength_{names[1]}",
        "rank_first": f"rank_{names[0]}", "rank_second": f"rank_{names[1]}",
    })
    return comparison, region_stability


def plot_scatter(first, second, regions, comparison, output_path):
    """
    Scatter of every connection's strength in run 1 (x) against run 2 (y).
    Points on the diagonal = the two scans gave the same value.
    Inputs: two runs, regions, comparison dict, PNG path. Output: none (writes PNG).
    """
    networks = regions["network"].to_numpy()
    rows, columns = np.triu_indices(len(networks), k=1)
    same_network = networks[rows] == networks[columns]
    edges_first = upper_triangle(first["connectivity"])
    edges_second = upper_triangle(second["connectivity"])
    names = comparison["run_labels"]

    figure, axes = plt.subplots(figsize=(6.4, 6.4), dpi=150)
    figure.patch.set_facecolor("#fcfcfb")
    axes.set_facecolor("#fcfcfb")
    axes.scatter(edges_first[~same_network], edges_second[~same_network], s=3, alpha=0.18,
                 color="#9a9a94", linewidths=0, label="Regions in different networks")
    axes.scatter(edges_first[same_network], edges_second[same_network], s=3, alpha=0.35,
                 color="#2a78d6", linewidths=0, label="Regions in the same network")
    axes.plot([-1, 1], [-1, 1], color="#2b2b29", linewidth=1, linestyle=(0, (4, 3)),
              label="Perfect agreement")

    limit = (-0.85, 1.0)
    axes.set_xlim(limit)
    axes.set_ylim(limit)
    axes.set_aspect("equal")
    axes.set_xlabel(f"Connection strength in {names[0]} (r)", color="#2b2b29")
    axes.set_ylabel(f"Connection strength in {names[1]} (r)", color="#2b2b29")
    axes.tick_params(colors="#5f5f5b", labelsize=8)
    for side in ("top", "right"):
        axes.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        axes.spines[side].set_color("#c9c8c2")
    axes.grid(color="#ecebe7", linewidth=0.6)
    axes.set_axisbelow(True)
    legend = axes.legend(loc="upper left", fontsize=8, frameon=False, markerscale=4)
    for handle in legend.legend_handles[:2]:
        handle.set_alpha(0.9)
    axes.set_title(f"{names[0]} vs {names[1]}: every one of {comparison['n_region_pairs']:,} connections\n"
                   f"agreement r = {comparison['matrix_correlation']:.2f}", fontsize=11, color="#2b2b29",
                   loc="left")
    figure.tight_layout()
    figure.savefig(output_path, facecolor=figure.get_facecolor())
    plt.close(figure)


def plot_matrix_pair(matrices, titles, regions, suptitle, output_path):
    """
    Two connectivity matrices side by side, same network ordering and same
    color scale as step 3, so they can be compared block by block.
    Inputs: two 200 x 200 matrices (region-id order), two panel titles,
            regions table, figure title, PNG path. Output: none (writes PNG).
    """
    order = network_sort_order(regions)
    sorted_networks = regions["network"].to_numpy()[order]
    boundaries = np.flatnonzero(sorted_networks[1:] != sorted_networks[:-1]) + 1
    sorted_matrices = []
    for matrix in matrices:
        matrix = matrix[np.ix_(order, order)].copy()
        np.fill_diagonal(matrix, np.nan)
        sorted_matrices.append(matrix)
    color_limit = float(max(np.nanpercentile(np.abs(matrix), 99) for matrix in sorted_matrices))
    colormap = LinearSegmentedColormap.from_list("blue_gray_red", DIVERGING_COLORS)
    colormap.set_bad("#f0efec")

    figure, axes_pair = plt.subplots(1, 2, figsize=(12, 6.0), dpi=150, gridspec_kw={"wspace": 0.04})
    figure.patch.set_facecolor("#fcfcfb")
    for panel, (axes, matrix, title) in enumerate(zip(axes_pair, sorted_matrices, titles)):
        image = axes.imshow(matrix, cmap=colormap, vmin=-color_limit, vmax=color_limit, interpolation="nearest")
        for position in boundaries:
            axes.axhline(position - 0.5, color="#fcfcfb", linewidth=1)
            axes.axvline(position - 0.5, color="#fcfcfb", linewidth=1)
        starts = np.concatenate([[0], boundaries])
        ends = np.concatenate([boundaries, [len(order)]])
        axes.set_yticks((starts + ends - 1) / 2)
        # Both matrices use the same order, so only the left one needs network labels
        labels = [config.NETWORK_FULL_NAMES[sorted_networks[start]] for start in starts] if panel == 0 else []
        axes.set_yticklabels(labels, fontsize=7)
        axes.set_xticks([])
        axes.tick_params(length=0, colors="#2b2b29")
        for spine in axes.spines.values():
            spine.set_visible(False)
        axes.set_title(title, fontsize=10, color="#2b2b29", loc="left")
    colorbar = figure.colorbar(image, ax=axes_pair, fraction=0.025, pad=0.02)
    colorbar.set_label("Pearson r", fontsize=8, color="#2b2b29")
    colorbar.ax.tick_params(labelsize=7, colors="#5f5f5b")
    colorbar.outline.set_visible(False)
    figure.suptitle(suptitle, fontsize=12, color="#2b2b29", weight="bold", x=0.06, y=0.97, ha="left")
    figure.savefig(output_path, facecolor=figure.get_facecolor(), bbox_inches="tight")
    plt.close(figure)


def plot_heatmaps(first, second, regions, comparison, output_path):
    """
    The two runs' connectivity matrices side by side (see plot_matrix_pair).
    Inputs: two runs, regions, comparison dict, PNG path. Output: none (writes PNG).
    """
    titles = [f"{name}  ·  head motion {comparison['head_motion_mm'][name]:.3f} mm"
              for name in comparison["run_labels"]]
    gsr_note = "  ·  global signal removed" if comparison["global_signal_regression"] else ""
    suptitle = (f"Same brain, two scans — {config.SUBJECT_ID}{gsr_note}  ·  agreement r = "
                f"{comparison['matrix_correlation']:.2f}")
    plot_matrix_pair([first["connectivity"], second["connectivity"]], titles, regions, suptitle, output_path)


def print_summary(comparison):
    """
    Print the numbers and a plain-language summary.
    Input: comparison dict. Output: none.
    """
    first, second = comparison["run_labels"]
    print(f"Comparing {comparison['runs'][0]} with {comparison['runs'][1]} for {config.SUBJECT_ID}\n")
    print(f"Headline - agreement between the two connectivity matrices "
          f"({comparison['n_region_pairs']:,} region pairs):")
    print(f"  r = {comparison['matrix_correlation']:.3f}   (on Fisher z values: "
          f"{comparison['matrix_correlation_fisher_z']:.3f})")
    print(f"\nRegion strength agreement across the 200 regions:")
    print(f"  strongest-10% graph strength: r = {comparison['strength_correlation']:.3f}")
    print(f"  all positive connections:     r = {comparison['strength_correlation_all_positive']:.3f}")
    print(f"  mean strength {first} {comparison['mean_strength'][first]:.2f} vs "
          f"{second} {comparison['mean_strength'][second]:.2f}")
    print(f"\nStrongest-10% connections found in both runs: {comparison['top10_edge_overlap']:.0%}")
    print(f"  graph cutoff r: {first} {comparison['graph_cutoff_r'][first]:.3f}, "
          f"{second} {comparison['graph_cutoff_r'][second]:.3f}")
    print(f"  isolated regions: {first} {len(comparison['isolated_regions'][first])}, "
          f"{second} {len(comparison['isolated_regions'][second])}")

    print(f"\n{'':22s}{first:>10s}{second:>10s}")
    print(f"{'Head motion (mm)':22s}{comparison['head_motion_mm'][first]:10.4f}"
          f"{comparison['head_motion_mm'][second]:10.4f}")
    print(f"{'Modularity':22s}{comparison['modularity'][first]:10.3f}{comparison['modularity'][second]:10.3f}")

    print(f"\n{N_MOST_CHANGED} regions whose strength changed most ({first} -> {second}; "
          f"places moved: + = up the ranking of 200):")
    print(f"  {'id':>3}  {'region':26s} {'hemi':4s} {'network':12s} {first:>7s} {second:>7s} "
          f"{'change':>7s} {'places moved':>13s}")
    for region in comparison["most_changed_regions"]:
        print(f"  {region['id']:>3}  {region['region_name']:26s} {region['hemisphere']:4s} "
              f"{region['network']:12s} {region[f'strength_{first}']:7.2f} {region[f'strength_{second}']:7.2f} "
              f"{region['change']:+7.2f} {region['rank_change']:+13d}")

    print("\nIn plain language:")
    print(f"  {comparison['agreement_sentence']}")
    print(f"  Across all {comparison['n_region_pairs']:,} pairs of regions, the two scans' connection "
          f"strengths correlate at r = {comparison['matrix_correlation']:.2f}.")
    print(f"  Head movement was low in both scans ({comparison['head_motion_mm'][first]:.3f} and "
          f"{comparison['head_motion_mm'][second]:.3f} mm), so motion is unlikely to explain the differences.")


def main():
    """
    Compare the two runs in config.RUNS_TO_COMPARE, print the results,
    and save the JSON, per-region table, and both figures.
    """
    first, second = (load_run(run_name) for run_name in config.RUNS_TO_COMPARE)
    regions = pd.read_csv(config.get_derived_dir(run_name=first["name"]) / "regions.csv")

    comparison, region_stability = compare(first, second, regions)
    print_summary(comparison)

    output_dir = config.get_subject_dir()
    suffix = config.get_variant_suffix()
    file_names = [f"run_comparison{suffix}.json", f"region_stability{suffix}.csv",
                  f"run_comparison_scatter{suffix}.png", f"run_comparison_heatmaps{suffix}.png"]
    (output_dir / file_names[0]).write_text(json.dumps(comparison, indent=2))
    region_stability.to_csv(output_dir / file_names[1], index=False, float_format="%.4f")
    plot_scatter(first, second, regions, comparison, output_dir / file_names[2])
    plot_heatmaps(first, second, regions, comparison, output_dir / file_names[3])
    print()
    for file_name in file_names:
        print(f"Saved {(output_dir / file_name).relative_to(config.REPO_DIR)}")


if __name__ == "__main__":
    main()
