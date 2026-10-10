"""
Step 4 - Place each region's graph node on the brain surface.

For each region: average the midthickness coordinates of its vertices (the
centroid), then move to the region's own vertex nearest that centroid, so the
node sits on the cortex (a centroid of a curved region can float in white
matter or even land in a neighbouring region).

Reads:  both midthickness meshes (raw) and the Schaefer atlas.
        data/derived/<subject>/<default run>/regions.csv (from step 2) for the region list.
Writes: data/derived/<subject>/node_positions.csv
          id, hemisphere, vertex_index, x, y, z, centroid_x/y/z, snap_distance_mm
        data/derived/<subject>/node_positions.png (quick visual check)

Node positions depend only on the mesh and atlas, not on the fMRI run, so they
are saved once per subject (not per run) and shared by every run.

vertex_index is the mesh vertex the node sits on. The pial / inflated meshes
use the same vertex numbering, so a later view toggle can reuse it.

Run:    python pipeline/step4_node_positions.py
"""

import config  # first: stops early with a clear message if the wrong Python is used

import matplotlib

matplotlib.use("Agg")  # draw to files only, no window
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from brain_io import load_atlas, load_mesh


def place_nodes(regions, brain_points, vertex_labels):
    """
    Find the on-surface node position for every region.
    Inputs: regions table (id, hemisphere), brain_points {"L"/"R": (32492, 3)},
            vertex_labels {"L"/"R": (32492,)} region id per vertex.
    Output: DataFrame with one row per region (see module docstring for columns).
    """
    rows = []
    for region in regions.itertuples():
        hemisphere = region.hemisphere
        region_vertices = np.flatnonzero(vertex_labels[hemisphere] == region.id)
        region_points = brain_points[hemisphere][region_vertices]

        centroid = region_points.mean(axis=0)
        distances = np.linalg.norm(region_points - centroid, axis=1)
        nearest = int(np.argmin(distances))
        snapped_vertex = int(region_vertices[nearest])
        x, y, z = brain_points[hemisphere][snapped_vertex]

        rows.append({
            "id": region.id,
            "hemisphere": hemisphere,
            "vertex_index": snapped_vertex,
            "x": float(x), "y": float(y), "z": float(z),
            "centroid_x": float(centroid[0]), "centroid_y": float(centroid[1]),
            "centroid_z": float(centroid[2]),
            "snap_distance_mm": float(distances[nearest]),
        })
    return pd.DataFrame(rows)


def check_positions(node_positions, regions, vertex_labels):
    """
    Print sanity checks on the node positions.
    Inputs: node_positions table, regions table, vertex_labels.
    Output: none (prints only).
    """
    left = node_positions[node_positions["hemisphere"] == "L"]
    right = node_positions[node_positions["hemisphere"] == "R"]
    on_own_region = all(
        vertex_labels[row.hemisphere][row.vertex_index] == row.id for row in node_positions.itertuples()
    )
    snap = node_positions["snap_distance_mm"]
    print("Checks:")
    print(f"  nodes: {len(node_positions)} (L {len(left)}, R {len(right)})")
    print(f"  every node sits on a vertex of its own region: {on_own_region}")
    print(f"  left nodes all have x < 0: {bool((left['x'] < 0).all())}   "
          f"right nodes all have x > 0: {bool((right['x'] > 0).all())}")
    print(f"  centroid -> surface snap distance (mm): median {snap.median():.1f}, max {snap.max():.1f}")
    farthest = node_positions.loc[snap.idxmax()]
    farthest_name = regions.loc[regions["id"] == farthest["id"], "full_name"].iloc[0]
    print(f"  largest snap: region {int(farthest['id'])} {farthest_name}")
    print(f"  x range {node_positions['x'].min():.1f} to {node_positions['x'].max():.1f}, "
          f"y range {node_positions['y'].min():.1f} to {node_positions['y'].max():.1f}, "
          f"z range {node_positions['z'].min():.1f} to {node_positions['z'].max():.1f} mm")


def plot_positions(node_positions, regions, brain_points, output_path):
    """
    Save a 3-view picture (top, left side, front) of the nodes over the mesh.
    Inputs: node_positions, regions (for network), brain_points, PNG path.
    Output: none (writes the PNG).
    """
    all_points = np.vstack([brain_points["L"], brain_points["R"]])[::4]  # thin out for speed
    networks = regions.set_index("id").loc[node_positions["id"], "network"].to_numpy()
    node_colors = [config.NETWORK_COLORS[network] for network in networks]

    # (title, horizontal axis, vertical axis, depth axis for drawing order)
    views = [("Top (looking down)", 0, 1, 2), ("Left side", 1, 2, 0), ("Front", 0, 2, 1)]
    figure, axes_list = plt.subplots(1, 3, figsize=(15, 5.4), dpi=120)
    figure.patch.set_facecolor("#fcfcfb")
    for axes, (title, horizontal, vertical, depth) in zip(axes_list, views):
        flip = -1 if title == "Left side" else 1  # looking at the left side, front is to the left
        axes.scatter(flip * all_points[:, horizontal], all_points[:, vertical], s=0.3,
                     color="#d6d5d0", linewidths=0)
        draw_order = np.argsort(node_positions[["x", "y", "z"]].to_numpy()[:, depth]
                                * (-1 if title == "Left side" else 1))
        coordinates = node_positions[["x", "y", "z"]].to_numpy()[draw_order]
        axes.scatter(flip * coordinates[:, horizontal], coordinates[:, vertical], s=34,
                     c=np.array(node_colors)[draw_order], edgecolors="#fcfcfb", linewidths=0.8)
        axes.set_title(title, fontsize=10, color="#2b2b29")
        axes.set_aspect("equal")
        axes.axis("off")

    handles = [plt.Line2D([], [], marker="o", linestyle="", markersize=7, color=color,
                          label=config.NETWORK_FULL_NAMES[network])
               for network, color in config.NETWORK_COLORS.items()]
    figure.legend(handles=handles, loc="lower center", ncol=7, frameon=False, fontsize=9)
    figure.suptitle(f"Region nodes on the midthickness surface — {config.SUBJECT_ID}",
                    fontsize=12, color="#2b2b29", weight="bold")
    figure.savefig(output_path, facecolor=figure.get_facecolor(), bbox_inches="tight")
    plt.close(figure)


def main():
    """
    Compute node positions for the configured subject, check them,
    and save the CSV and the picture.
    """
    output_dir = config.get_subject_dir()
    raw_paths = config.get_raw_paths(surface="midthickness")
    regions = pd.read_csv(config.get_derived_dir() / "regions.csv")

    brain_points = {hemisphere: load_mesh(raw_paths[f"mesh_{hemisphere}"])[0] for hemisphere in ("L", "R")}
    vertex_labels, _label_table = load_atlas(config.ATLAS_DLABEL, config.VERTICES_PER_HEMISPHERE)

    node_positions = place_nodes(regions, brain_points, vertex_labels)
    check_positions(node_positions, regions, vertex_labels)

    node_positions.to_csv(output_dir / "node_positions.csv", index=False, float_format="%.3f")
    plot_positions(node_positions, regions, brain_points, output_dir / "node_positions.png")
    print(f"\nSaved {(output_dir / 'node_positions.csv').relative_to(config.REPO_DIR)}")
    print(f"Saved {(output_dir / 'node_positions.png').relative_to(config.REPO_DIR)}")


if __name__ == "__main__":
    main()
