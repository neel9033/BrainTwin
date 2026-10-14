"""
Step 5 - Build the brain graph and measure it.

Nodes are the 200 regions. For graph measures we keep only the strongest
connections: the top GRAPH_DENSITY fraction of all region pairs, ranked by
correlation, positive values only (config.GRAPH_DENSITY, default 10%).
Edge weight = Pearson r. The full unthresholded matrix stays in
connectivity.npy for the website export.

Reads:  data/derived/<subject>/<run>/connectivity.npy and regions.csv (steps 2-3),
        head-motion file (raw) for QC.
Writes: data/derived/<subject>/<run>/region_stats.csv   one row per region
        data/derived/<subject>/<run>/graph_edges.csv    the kept (thresholded) edges
        data/derived/<subject>/<run>/graph_summary.json whole-brain numbers + QC

Run:    python pipeline/step5_graph_stats.py                    (default run)
        python pipeline/step5_graph_stats.py --run rfMRI_REST2_LR (another run)
"""

import config  # first: stops early with a clear message if the wrong Python is used

import json

import networkx as nx
import numpy as np
import pandas as pd


def threshold_strongest(correlation, density):
    """
    Keep the strongest positive connections so the graph has the given density.
    Inputs: correlation (regions x regions), density (e.g. 0.10).
    Output: DataFrame of kept edges with columns source, target, weight
            (source/target are row positions 0..n-1, sorted strongest first).
    """
    n_regions = len(correlation)
    rows, columns = np.triu_indices(n_regions, k=1)  # each pair once
    weights = correlation[rows, columns]
    n_to_keep = int(round(density * len(weights)))

    positive = weights > 0
    if positive.sum() < n_to_keep:
        print(f"  note: only {positive.sum()} positive pairs, fewer than the {n_to_keep} requested")
        n_to_keep = int(positive.sum())

    strongest_first = np.argsort(weights)[::-1][:n_to_keep]
    return pd.DataFrame({
        "source": rows[strongest_first],
        "target": columns[strongest_first],
        "weight": weights[strongest_first],
    })


def build_graph(regions, edges):
    """
    Make a weighted networkx graph with every region as a node (even if it
    ends up with no edges).
    Inputs: regions table, edges table from threshold_strongest().
    Output: networkx Graph. Node keys are region ids. Each edge has
            "weight" (= r, bigger is stronger) and "distance" (= 1 / r,
            used for shortest paths, so strong links count as short).
    """
    region_ids = regions["id"].to_numpy()
    graph = nx.Graph()
    for region in regions.itertuples():
        graph.add_node(int(region.id), network=region.network, hemisphere=region.hemisphere)
    for edge in edges.itertuples():
        graph.add_edge(int(region_ids[edge.source]), int(region_ids[edge.target]),
                       weight=float(edge.weight), distance=1.0 / float(edge.weight))
    return graph


def eigenvector_centrality_safe(graph):
    """
    Weighted eigenvector centrality that also works if the graph has more than
    one piece: computed on the largest connected piece, 0 for everyone else.
    Input: graph. Output: dict {region id: centrality}.
    """
    centrality = {node: 0.0 for node in graph.nodes}
    largest_piece = graph.subgraph(max(nx.connected_components(graph), key=len))
    centrality.update(nx.eigenvector_centrality_numpy(largest_piece, weight="weight"))
    return centrality


def region_measures(graph, regions):
    """
    Compute the per-region graph measures.
    Inputs: graph, regions table.
    Output: DataFrame: region info + degree, strength, betweenness,
            clustering, eigenvector.
    """
    degree = dict(graph.degree())                         # number of kept connections
    strength = dict(graph.degree(weight="weight"))        # sum of kept connection weights
    betweenness = nx.betweenness_centrality(graph, weight="distance", normalized=True)
    clustering = nx.clustering(graph, weight="weight")    # weighted (Onnela) clustering
    eigenvector = eigenvector_centrality_safe(graph)

    region_stats = regions[["id", "full_name", "region_name", "hemisphere", "network"]].copy()
    region_stats["degree"] = region_stats["id"].map(degree)
    region_stats["strength"] = region_stats["id"].map(strength)
    region_stats["betweenness"] = region_stats["id"].map(betweenness)
    region_stats["clustering"] = region_stats["id"].map(clustering)
    region_stats["eigenvector"] = region_stats["id"].map(eigenvector)
    return region_stats


def whole_brain_summary(graph, region_stats, edges, mean_motion_mm, run_name):
    """
    Compute whole-brain graph numbers and the left-vs-right comparison.
    Inputs: graph, region_stats table, kept edges, mean head motion (mm), run_name.
    Output: dict ready to save as JSON.
    """
    communities = [
        {node for node, data in graph.nodes(data=True) if data["network"] == network}
        for network in config.NETWORK_ORDER
    ]
    pieces = list(nx.connected_components(graph))

    left_vs_right = {}
    for network in config.NETWORK_ORDER:
        in_network = region_stats[region_stats["network"] == network]
        left_vs_right[network] = {
            hemisphere: float(in_network.loc[in_network["hemisphere"] == hemisphere, "strength"].mean())
            for hemisphere in ("L", "R")
        }

    same_network = np.array([
        graph.nodes[source]["network"] == graph.nodes[target]["network"] for source, target in graph.edges
    ])
    same_hemisphere = np.array([
        graph.nodes[source]["hemisphere"] == graph.nodes[target]["hemisphere"] for source, target in graph.edges
    ])

    return {
        "subject_id": config.SUBJECT_ID,
        "hcp_id": config.get_hcp_id(),
        "run_name": run_name,
        "global_signal_regression": config.get_use_gsr(),
        "threshold": {
            "method": "keep strongest positive correlations (proportional threshold)",
            "density_requested": config.GRAPH_DENSITY,
            "edges_kept": int(graph.number_of_edges()),
            "weakest_kept_r": float(edges["weight"].min()),
            "strongest_kept_r": float(edges["weight"].max()),
        },
        "n_nodes": int(graph.number_of_nodes()),
        "density": float(nx.density(graph)),
        "connected_pieces": len(pieces),
        "largest_piece_size": int(max(len(piece) for piece in pieces)),
        "isolated_regions": sorted(int(node) for node in nx.isolates(graph)),
        "average_clustering": float(nx.average_clustering(graph, weight="weight")),
        "modularity_schaefer_networks": float(nx.community.modularity(graph, communities, weight="weight")),
        "fraction_edges_within_network": float(same_network.mean()),
        "fraction_edges_within_hemisphere": float(same_hemisphere.mean()),
        "mean_strength_by_network_and_hemisphere": left_vs_right,
        "qc": {
            "mean_relative_motion_mm": mean_motion_mm,
        },
    }


def print_top(region_stats, column, n_top=10):
    """
    Print the n_top regions ranked by one measure.
    Inputs: region_stats table, column name, how many to show. Output: none.
    """
    top = region_stats.sort_values(column, ascending=False).head(n_top)
    print(f"\nTop {n_top} regions by {column}:")
    print(f"  {'rank':>4}  {'id':>3}  {'region':28s} {'hemi':4s} {'network':12s} {column:>11s}  degree")
    for rank, row in enumerate(top.itertuples(), start=1):
        print(f"  {rank:>4}  {row.id:>3}  {row.region_name:28s} {row.hemisphere:4s} {row.network:12s} "
              f"{getattr(row, column):11.3f}  {row.degree:>6}")


def main():
    """
    Threshold the connectivity matrix, build the graph, compute all measures,
    print the checkpoint tables, and save everything.
    """
    run_name = config.get_run_name()
    output_dir = config.get_derived_dir(run_name=run_name)
    correlation = np.load(output_dir / "connectivity.npy")
    regions = pd.read_csv(output_dir / "regions.csv")
    mean_motion_mm = float(np.loadtxt(config.get_raw_paths(run_name=run_name)["motion"]))

    edges = threshold_strongest(correlation, config.GRAPH_DENSITY)
    graph = build_graph(regions, edges)
    region_stats = region_measures(graph, regions)
    summary = whole_brain_summary(graph, region_stats, edges, mean_motion_mm, run_name)

    threshold = summary["threshold"]
    print(f"Graph: {summary['n_nodes']} nodes, {threshold['edges_kept']} edges "
          f"(density {summary['density']:.3f}), kept r from {threshold['weakest_kept_r']:.3f} "
          f"to {threshold['strongest_kept_r']:.3f}")
    print(f"Connected pieces: {summary['connected_pieces']} (largest has {summary['largest_piece_size']} "
          f"regions); isolated regions: {summary['isolated_regions'] or 'none'}")
    print(f"Average clustering: {summary['average_clustering']:.3f}")
    print(f"Modularity (Schaefer networks as communities): {summary['modularity_schaefer_networks']:.3f}")
    print(f"Edges within the same network: {summary['fraction_edges_within_network']:.0%}, "
          f"within the same hemisphere: {summary['fraction_edges_within_hemisphere']:.0%}")
    print(f"Mean head motion (QC): {mean_motion_mm:.4f} mm")

    print("\nMean strength per network, left vs right hemisphere:")
    print(f"  {'network':12s} {'L':>6s} {'R':>6s}")
    for network, values in summary["mean_strength_by_network_and_hemisphere"].items():
        print(f"  {network:12s} {values['L']:6.2f} {values['R']:6.2f}")

    print_top(region_stats, "strength")
    print_top(region_stats, "betweenness")

    # Save edges with region ids (not row positions)
    region_ids = regions["id"].to_numpy()
    edges_with_ids = edges.assign(source=region_ids[edges["source"]], target=region_ids[edges["target"]])
    edges_with_ids.to_csv(output_dir / "graph_edges.csv", index=False, float_format="%.5f")
    region_stats.to_csv(output_dir / "region_stats.csv", index=False, float_format="%.6f")
    (output_dir / "graph_summary.json").write_text(json.dumps(summary, indent=2))
    print()
    for file_name in ["region_stats.csv", "graph_edges.csv", "graph_summary.json"]:
        print(f"Saved {(output_dir / file_name).relative_to(config.REPO_DIR)}")


if __name__ == "__main__":
    main()
