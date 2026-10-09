"""
Step 3 - Functional connectivity: correlation between every pair of regions.

Reads:  data/derived/<subject>/region_timeseries.npy and regions.csv (from step 2).
Writes: data/derived/<subject>/connectivity.npy          (200 x 200 Pearson r)
        data/derived/<subject>/connectivity_fisher_z.npy (200 x 200 Fisher z, diagonal = 0)
        data/derived/<subject>/connectivity_checks.json  (results of the checks below)
        data/derived/<subject>/connectivity_heatmap.png  (matrix sorted by network)

Run:    python pipeline/step3_connectivity.py
"""

import json

import matplotlib

matplotlib.use("Agg")  # draw to files only, no window
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap

import config

# Diverging colors for the heatmap: blue = negative, gray = zero, red = positive
DIVERGING_COLORS = ["#104281", "#2a78d6", "#f0efec", "#e34948", "#9e1b1f"]


def compute_connectivity(region_timeseries):
    """
    Pearson correlation between every pair of region time series.
    Input: region_timeseries (timepoints x regions).
    Output: (correlation, fisher_z), both (regions x regions) float64.
            fisher_z = arctanh(r); its diagonal is set to 0 because arctanh(1) is infinite.
    """
    correlation = np.corrcoef(region_timeseries.T.astype(np.float64))
    off_diagonal = ~np.eye(len(correlation), dtype=bool)
    fisher_z = np.zeros_like(correlation)
    fisher_z[off_diagonal] = np.arctanh(correlation[off_diagonal])
    return correlation, fisher_z


def check_matrix(correlation, regions):
    """
    Run the sanity checks on the correlation matrix and print them.
    Inputs: correlation (regions x regions), regions table from step 2.
    Output: dict of check results (also saved to JSON).
    """
    off_diagonal = ~np.eye(len(correlation), dtype=bool)
    off_values = correlation[off_diagonal]
    checks = {
        "shape": list(correlation.shape),
        "symmetric": bool(np.allclose(correlation, correlation.T)),
        "diagonal_all_one": bool(np.allclose(np.diag(correlation), 1.0)),
        "within_minus1_to_1": bool(np.all((correlation >= -1) & (correlation <= 1))),
        "has_nan": bool(np.isnan(correlation).any()),
        "off_diagonal_min": float(off_values.min()),
        "off_diagonal_max": float(off_values.max()),
        "off_diagonal_mean": float(off_values.mean()),
        "fraction_positive": float((off_values > 0).mean()),
    }

    # Same-network pairs should correlate more than different-network pairs
    networks = regions["network"].to_numpy()
    same_network = (networks[:, None] == networks[None, :]) & off_diagonal
    different_network = networks[:, None] != networks[None, :]
    checks["mean_r_same_network"] = float(correlation[same_network].mean())
    checks["mean_r_different_network"] = float(correlation[different_network].mean())

    per_network = {}
    for network in config.NETWORK_ORDER:
        in_network = networks == network
        within_block = correlation[np.ix_(in_network, in_network)]
        within_values = within_block[~np.eye(in_network.sum(), dtype=bool)]
        to_others = correlation[np.ix_(in_network, ~in_network)]
        per_network[network] = {
            "within": float(within_values.mean()),
            "to_other_networks": float(to_others.mean()),
        }
    checks["mean_r_per_network"] = per_network

    print("Checks:")
    for key in ["shape", "symmetric", "diagonal_all_one", "within_minus1_to_1", "has_nan"]:
        print(f"  {key:22s} {checks[key]}")
    print(f"  off-diagonal r: min {checks['off_diagonal_min']:.3f}, "
          f"max {checks['off_diagonal_max']:.3f}, mean {checks['off_diagonal_mean']:.3f}, "
          f"{checks['fraction_positive']:.0%} positive")
    print(f"\nMean r, same network: {checks['mean_r_same_network']:.3f}  vs  "
          f"different networks: {checks['mean_r_different_network']:.3f}")
    print(f"  {'network':12s} {'within':>7s} {'to others':>10s}")
    for network, values in per_network.items():
        print(f"  {network:12s} {values['within']:7.3f} {values['to_other_networks']:10.3f}")
    return checks


def network_sort_order(regions):
    """
    Order regions by network (atlas order), then hemisphere (L then R), then id.
    Input: regions table. Output: int array of row positions in sorted order.
    """
    network_rank = regions["network"].map({name: rank for rank, name in enumerate(config.NETWORK_ORDER)})
    sort_table = pd.DataFrame({"network_rank": network_rank, "hemisphere": regions["hemisphere"],
                               "id": regions["id"]})
    return sort_table.sort_values(["network_rank", "hemisphere", "id"]).index.to_numpy()


def plot_heatmap(correlation, regions, output_path):
    """
    Save a heatmap of the correlation matrix with regions grouped by network.
    Inputs: correlation (regions x regions), regions table, output PNG path.
    Output: none (writes the PNG). The diagonal is hidden since it is always 1.
    """
    order = network_sort_order(regions)
    sorted_matrix = correlation[np.ix_(order, order)].copy()
    np.fill_diagonal(sorted_matrix, np.nan)
    sorted_networks = regions["network"].to_numpy()[order]

    # Symmetric color limits so zero sits at the gray midpoint
    color_limit = float(np.nanpercentile(np.abs(sorted_matrix), 99))
    colormap = LinearSegmentedColormap.from_list("blue_gray_red", DIVERGING_COLORS)
    colormap.set_bad("#f0efec")

    # Lay the panels out in inches, then convert to figure fractions
    figure_width, figure_height = 11.3, 9.0
    label_margin, bottom_margin, matrix_size = 2.6, 0.3, 7.4
    strip_size, strip_gap = 0.22, 0.04

    def place(left, bottom, width, height):
        """Add axes at a position given in inches. Output: matplotlib Axes."""
        return figure.add_axes([left / figure_width, bottom / figure_height,
                                width / figure_width, height / figure_height])

    figure = plt.figure(figsize=(figure_width, figure_height), dpi=150)
    figure.patch.set_facecolor("#fcfcfb")
    matrix_axes = place(label_margin, bottom_margin, matrix_size, matrix_size)
    left_strip = place(label_margin - strip_size - strip_gap, bottom_margin, strip_size, matrix_size)
    top_strip = place(label_margin, bottom_margin + matrix_size + strip_gap, matrix_size, strip_size)
    colorbar_axes = place(label_margin + matrix_size + 0.3, bottom_margin + matrix_size * 0.3,
                          0.16, matrix_size * 0.4)
    title_y = (bottom_margin + matrix_size + strip_gap + strip_size + 0.65) / figure_height

    image = matrix_axes.imshow(sorted_matrix, cmap=colormap, vmin=-color_limit, vmax=color_limit,
                               interpolation="nearest")
    matrix_axes.set_xticks([])
    matrix_axes.set_yticks([])
    for spine in matrix_axes.spines.values():
        spine.set_visible(False)

    # Network boundaries (thin surface-colored lines) and color strips with labels
    boundaries = np.flatnonzero(sorted_networks[1:] != sorted_networks[:-1]) + 1
    for position in boundaries:
        matrix_axes.axhline(position - 0.5, color="#fcfcfb", linewidth=1.2)
        matrix_axes.axvline(position - 0.5, color="#fcfcfb", linewidth=1.2)

    starts = np.concatenate([[0], boundaries])
    ends = np.concatenate([boundaries, [len(sorted_networks)]])
    for strip in (left_strip, top_strip):
        strip.set_xlim(0, 1) if strip is left_strip else strip.set_xlim(-0.5, len(order) - 0.5)
        strip.set_ylim(len(order) - 0.5, -0.5) if strip is left_strip else strip.set_ylim(0, 1)
        strip.axis("off")
    for start, end in zip(starts, ends):
        network = sorted_networks[start]
        color = config.NETWORK_COLORS[network]
        left_strip.add_patch(plt.Rectangle((0, start - 0.5), 1, end - start, color=color, linewidth=0))
        top_strip.add_patch(plt.Rectangle((start - 0.5, 0), end - start, 1, color=color, linewidth=0))
        left_strip.text(-0.4, (start + end - 1) / 2, f"{config.NETWORK_FULL_NAMES[network]}  ({end - start})",
                        ha="right", va="center", fontsize=9, color="#2b2b29")

    colorbar = figure.colorbar(image, cax=colorbar_axes)
    colorbar.set_label("Pearson r", fontsize=9, color="#2b2b29")
    colorbar.ax.tick_params(labelsize=8, colors="#5f5f5b")
    colorbar.outline.set_visible(False)

    title_x = label_margin / figure_width
    figure.text(title_x, title_y, f"Functional connectivity — {config.SUBJECT_ID} (HCP {config.get_hcp_id()}), "
                f"{config.RUN_NAME}", fontsize=12, color="#2b2b29", weight="bold")
    figure.text(title_x, title_y - 0.3 / figure_height,
                "200 Schaefer regions sorted by network (left then right hemisphere within each); "
                "diagonal hidden", fontsize=8.5, color="#5f5f5b")
    figure.savefig(output_path, facecolor=figure.get_facecolor())
    plt.close(figure)


def main():
    """
    Load step 2 outputs, compute both connectivity matrices, check them,
    and save matrices, checks, and heatmap.
    """
    output_dir = config.get_derived_dir()
    region_timeseries = np.load(output_dir / "region_timeseries.npy")
    regions = pd.read_csv(output_dir / "regions.csv")
    print(f"Loaded region_timeseries {region_timeseries.shape} and {len(regions)} regions\n")

    correlation, fisher_z = compute_connectivity(region_timeseries)
    checks = check_matrix(correlation, regions)
    checks["fisher_z_range"] = [float(fisher_z.min()), float(fisher_z.max())]
    print(f"\nFisher z range: {checks['fisher_z_range'][0]:.3f} to {checks['fisher_z_range'][1]:.3f} "
          f"(diagonal set to 0)")

    np.save(output_dir / "connectivity.npy", correlation)
    np.save(output_dir / "connectivity_fisher_z.npy", fisher_z)
    (output_dir / "connectivity_checks.json").write_text(json.dumps(checks, indent=2))
    plot_heatmap(correlation, regions, output_dir / "connectivity_heatmap.png")

    for file_name in ["connectivity.npy", "connectivity_fisher_z.npy", "connectivity_checks.json",
                      "connectivity_heatmap.png"]:
        print(f"Saved {(output_dir / file_name).relative_to(config.REPO_DIR)}")


if __name__ == "__main__":
    main()
