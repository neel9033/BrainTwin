"""
Step 6 - Write the files the website loads.

Reads:  raw midthickness meshes + Schaefer atlas, and from data/derived/<subject>/:
        regions.csv, node_positions.csv, region_stats.csv, connectivity.npy,
        graph_edges.csv, graph_summary.json (steps 2-5).
Writes: web/public/data/<subject>/
          mesh_L_points.bin, mesh_R_points.bin       Float32, x y z per vertex (mm)
          mesh_L_triangles.bin, mesh_R_triangles.bin Uint32, 3 vertex indices per triangle
          mesh_L_region.bin, mesh_R_region.bin       Uint16, region id per vertex (0 = medial wall)
          graph.json    networks, nodes (position + all stats + top connections), edges
          subject.json  ids, run, counts, QC, graph summary, and how to read each file

All binary files are raw little-endian arrays with no header: the website
reads them with e.g. new Float32Array(buffer). Shapes are listed in subject.json.

Run:    python pipeline/step6_export_web.py
"""

import config  # first: stops early with a clear message if the wrong Python is used

import json
import sys

import numpy as np
import pandas as pd

from brain_io import load_atlas, load_mesh

STAT_COLUMNS = ["degree", "strength", "betweenness", "clustering", "eigenvector"]


def write_binary(array, path, dtype):
    """
    Save a numpy array as a raw little-endian binary file.
    Inputs: array, output path, dtype string (e.g. "<f4" for Float32).
    Output: dict describing the file (name, dtype, shape, bytes) for subject.json.
    """
    data = np.ascontiguousarray(array, dtype=dtype)
    data.tofile(path)
    return {"file": path.name, "dtype": np.dtype(dtype).name, "shape": list(data.shape),
            "bytes": int(path.stat().st_size)}


def export_meshes(output_dir):
    """
    Write mesh points, triangles, and per-vertex region ids for both hemispheres.
    Input: output folder.
    Output: (file_info list, mesh_counts dict, bounding box dict)
    """
    raw_paths = config.get_raw_paths(surface="midthickness")
    vertex_labels, _label_table = load_atlas(config.ATLAS_DLABEL, config.VERTICES_PER_HEMISPHERE)

    file_info, mesh_counts, all_points = [], {}, []
    for hemisphere in ("L", "R"):
        brain_points, triangles = load_mesh(raw_paths[f"mesh_{hemisphere}"])
        region_per_vertex = vertex_labels[hemisphere]

        file_info.append(write_binary(brain_points, output_dir / f"mesh_{hemisphere}_points.bin", "<f4"))
        file_info.append(write_binary(triangles, output_dir / f"mesh_{hemisphere}_triangles.bin", "<u4"))
        file_info.append(write_binary(region_per_vertex, output_dir / f"mesh_{hemisphere}_region.bin", "<u2"))

        mesh_counts[hemisphere] = {
            "vertices": int(len(brain_points)),
            "triangles": int(len(triangles)),
            "vertices_with_region": int((region_per_vertex > 0).sum()),
        }
        all_points.append(brain_points)

    all_points = np.vstack(all_points)
    bounding_box = {"min": [round(float(value), 2) for value in all_points.min(axis=0)],
                    "max": [round(float(value), 2) for value in all_points.max(axis=0)]}
    return file_info, mesh_counts, bounding_box


def top_connections(correlation, region_ids, row, how_many):
    """
    List one region's strongest partners from the FULL correlation matrix
    (so regions with no edges in the thresholded graph still have partners).
    Inputs: correlation matrix, region id array, the region's row, how many to list.
    Output: list of {"id": partner region id, "weight": r}, strongest first.
    """
    values = correlation[row].copy()
    values[row] = -np.inf  # skip the region itself
    strongest = np.argsort(values)[::-1][:how_many]
    return [{"id": int(region_ids[partner]), "weight": round(float(values[partner]), 4)}
            for partner in strongest]


def build_graph_json(output_dir_derived):
    """
    Combine regions, positions, stats and connectivity into one graph object.
    Input: the derived-data folder for this subject.
    Output: (graph dict, number of exported edges, how many of those are in the density graph)
    """
    regions = pd.read_csv(output_dir_derived / "regions.csv")
    node_positions = pd.read_csv(output_dir_derived / "node_positions.csv")
    region_stats = pd.read_csv(output_dir_derived / "region_stats.csv")
    correlation = np.load(output_dir_derived / "connectivity.npy")
    graph_edges = pd.read_csv(output_dir_derived / "graph_edges.csv")

    nodes_table = (regions
                   .merge(node_positions[["id", "vertex_index", "x", "y", "z"]], on="id")
                   .merge(region_stats[["id"] + STAT_COLUMNS], on="id"))
    region_ids = regions["id"].to_numpy()

    nodes = []
    for row_position, node in enumerate(nodes_table.itertuples()):
        nodes.append({
            "id": int(node.id),
            "name": node.region_name,
            "full_name": node.full_name,
            "hemisphere": node.hemisphere,
            "network": node.network,
            "color": node.color,
            "vertex_count": int(node.vertex_count),
            "vertex_index": int(node.vertex_index),
            "x": round(float(node.x), 2), "y": round(float(node.y), 2), "z": round(float(node.z), 2),
            "stats": {
                "degree": int(node.degree),
                "strength": round(float(node.strength), 4),
                "betweenness": round(float(node.betweenness), 5),
                "clustering": round(float(node.clustering), 5),
                "eigenvector": round(float(node.eigenvector), 5),
            },
            "top_connections": top_connections(correlation, region_ids, row_position,
                                               config.EXPORT_TOP_CONNECTIONS),
        })

    # Edges: every pair above the export threshold. in_graph = 1 if the edge is
    # also one of the strongest-density edges used for the graph measures.
    graph_pairs = {(min(s, t), max(s, t)) for s, t in zip(graph_edges["source"], graph_edges["target"])}
    rows, columns = np.triu_indices(len(region_ids), k=1)
    weights = correlation[rows, columns]
    keep = weights > config.EXPORT_EDGE_MIN_R
    edges = []
    for row, column, weight in zip(rows[keep], columns[keep], weights[keep]):
        source, target = int(region_ids[row]), int(region_ids[column])
        edges.append({"source": source, "target": target, "weight": round(float(weight), 4),
                      "in_graph": int((source, target) in graph_pairs)})
    edges.sort(key=lambda edge: -edge["weight"])

    networks = [{"id": network, "name": config.NETWORK_FULL_NAMES[network],
                 "color": config.NETWORK_COLORS[network]} for network in config.NETWORK_ORDER]

    graph = {
        "networks": networks,
        "edge_min_weight": config.EXPORT_EDGE_MIN_R,
        "graph_density": config.GRAPH_DENSITY,
        "nodes": nodes,
        "edges": edges,
    }
    return graph, len(edges), int(sum(edge["in_graph"] for edge in edges))


def write_json(data, path):
    """
    Save a dict as compact JSON (no extra spaces, to keep it small).
    Inputs: data dict, output path. Output: dict describing the file.
    """
    path.write_text(json.dumps(data, separators=(",", ":")))
    return {"file": path.name, "bytes": int(path.stat().st_size)}


def check_export(output_dir, graph, mesh_counts):
    """
    Read the binary files back and confirm they match what we meant to write.
    Inputs: output folder, graph dict, mesh_counts. Output: True if all checks pass.
    """
    all_good = True
    print("Checks (reading files back):")
    for hemisphere in ("L", "R"):
        n_vertices = mesh_counts[hemisphere]["vertices"]
        points = np.fromfile(output_dir / f"mesh_{hemisphere}_points.bin", dtype="<f4").reshape(-1, 3)
        triangles = np.fromfile(output_dir / f"mesh_{hemisphere}_triangles.bin", dtype="<u4").reshape(-1, 3)
        region_ids = np.fromfile(output_dir / f"mesh_{hemisphere}_region.bin", dtype="<u2")
        ok = (len(points) == n_vertices and len(region_ids) == n_vertices
              and triangles.max() < n_vertices and len(triangles) == mesh_counts[hemisphere]["triangles"])
        hemisphere_ids = sorted(set(np.unique(region_ids)) - {0})
        print(f"  {hemisphere}: {len(points):,} points, {len(triangles):,} triangles, "
              f"{len(hemisphere_ids)} region ids ({hemisphere_ids[0]}-{hemisphere_ids[-1]}) -> "
              f"{'OK' if ok else 'PROBLEM'}")
        all_good &= ok

        # Each node should sit on a vertex labelled with its own region
        for node in graph["nodes"]:
            if node["hemisphere"] == hemisphere and region_ids[node["vertex_index"]] != node["id"]:
                print(f"  PROBLEM: node {node['id']} vertex is labelled {region_ids[node['vertex_index']]}")
                all_good = False

    node_ids = {node["id"] for node in graph["nodes"]}
    edges_valid = all(edge["source"] in node_ids and edge["target"] in node_ids for edge in graph["edges"])
    nodes_with_edges = {edge["source"] for edge in graph["edges"]} | {edge["target"] for edge in graph["edges"]}
    print(f"  nodes: {len(graph['nodes'])}, all edge endpoints are real nodes: {edges_valid}")
    print(f"  nodes with at least one exported edge: {len(nodes_with_edges)} / {len(node_ids)}")
    print(f"  every node sits on a vertex of its own region: {all_good}")
    return all_good and edges_valid


def main():
    """
    Export meshes, graph and subject info for the website, check them,
    and print the file sizes.
    """
    derived_dir = config.get_derived_dir()
    output_dir = config.WEB_DATA_DIR / config.SUBJECT_ID
    output_dir.mkdir(parents=True, exist_ok=True)

    mesh_files, mesh_counts, bounding_box = export_meshes(output_dir)
    graph, n_edges, n_graph_edges = build_graph_json(derived_dir)
    graph_file = write_json(graph, output_dir / "graph.json")
    graph_summary = json.loads((derived_dir / "graph_summary.json").read_text())

    subject = {
        "subject_id": config.SUBJECT_ID,
        "hcp_id": config.get_hcp_id(),
        "run_name": config.RUN_NAME,
        "atlas": config.ATLAS_NAME,
        "surface": "midthickness_MSMAll",
        "coordinate_space": "MNINonLinear (mm)",
        "bounding_box_mm": bounding_box,
        "counts": {
            "regions": len(graph["nodes"]),
            "mesh": mesh_counts,
            "timepoints": int(np.load(derived_dir / "region_timeseries.npy", mmap_mode="r").shape[0]),
            "edges_exported": n_edges,
            "edges_in_graph": n_graph_edges,
        },
        "qc": graph_summary["qc"],
        "graph_summary": {key: graph_summary[key] for key in [
            "density", "average_clustering", "modularity_schaefer_networks", "connected_pieces",
            "isolated_regions", "fraction_edges_within_network", "mean_strength_by_network_and_hemisphere"]},
        "files": mesh_files + [graph_file],
    }
    subject_file = write_json(subject, output_dir / "subject.json")

    all_good = check_export(output_dir, graph, mesh_counts)
    print(f"  edges exported (r > {config.EXPORT_EDGE_MIN_R}): {n_edges:,}, "
          f"of which in the {config.GRAPH_DENSITY:.0%} graph: {n_graph_edges:,}")

    print(f"\nFiles in {output_dir.relative_to(config.REPO_DIR)}:")
    total_bytes = 0
    for info in subject["files"] + [subject_file]:
        total_bytes += info["bytes"]
        print(f"  {info['file']:24s} {info['bytes'] / 1024:8.1f} KB")
    print(f"  {'TOTAL':24s} {total_bytes / 1024 / 1024:8.2f} MB")

    if not all_good:
        sys.exit("Export checks failed - see PROBLEM lines above.")


if __name__ == "__main__":
    main()
