# Graph Report - braintwin  (2026-10-13)

## Corpus Check
- 33 files · ~20,689 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 3 file(s) not represented in the graph (top: (none) 1, .csv 1, .css 1)

## Summary
- 332 nodes · 736 edges · 8 communities
- Extraction: 99% EXTRACTED · 1% INFERRED · 0% AMBIGUOUS · INFERRED: 8 edges (avg confidence: 0.82)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `9fb98784`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- numpy
- step1_load_check.py
- step0_fetch_subject.py
- NetworkLayer.jsx
- App.jsx
- package.json
- Step-by-Step Python Pipeline
- config.py

## God Nodes (most connected - your core abstractions)
1. `App()` - 18 edges
2. `get_derived_dir()` - 16 edges
3. `main()` - 14 edges
4. `main()` - 14 edges
5. `load_atlas()` - 13 edges
6. `main()` - 13 edges
7. `main()` - 13 edges
8. `load_mesh()` - 12 edges
9. `main()` - 12 edges
10. `NetworkLayer()` - 12 edges

## Surprising Connections (you probably didn't know these)
- `Static React Three Fiber Website (no backend)` --references--> `Website HTML Entry Page`  [INFERRED]
  README.md → web/index.html
- `Step 0: Fetch Subject from HCP S3` --conceptually_related_to--> `boto3 Dependency`  [INFERRED]
  README.md → environment.yml
- `Step-by-Step Python Pipeline` --conceptually_related_to--> `networkx Dependency`  [INFERRED]
  README.md → environment.yml
- `Step-by-Step Python Pipeline` --conceptually_related_to--> `nibabel Dependency`  [INFERRED]
  README.md → environment.yml
- `verify_file()` --calls--> `load_mesh()`  [EXTRACTED]
  pipeline/step0_fetch_subject.py → pipeline/brain_io.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **HCP Data Access Flow** — readme_connectomedb, readme_hcp_data_use_terms, readme_hcp_credentials_file, readme_hcp_openaccess_s3_bucket, readme_subject_fetch_step [EXTRACTED 0.95]

## Communities (8 total, 0 thin omitted)

### Community 0 - "numpy"
Cohesion: 0.05
Nodes (31): check_matrix(), compute_connectivity(), main(), network_sort_order(), plot_heatmap(), build_graph(), eigenvector_centrality_safe(), main() (+23 more)

### Community 1 - "step1_load_check.py"
Cohesion: 0.08
Nodes (19): get_cortex_columns(), load_atlas(), load_mesh(), parse_region_name(), get_hcp_id(), get_raw_paths(), check_atlas(), check_files_only() (+11 more)

### Community 2 - "step0_fetch_subject.py"
Cohesion: 0.10
Nodes (9): check_python_environment(), get_raw_paths_for_hcp_id(), fetch_subject(), files_to_fetch(), format_size(), load_credentials(), main(), ProgressPrinter (+1 more)

### Community 3 - "NetworkLayer.jsx"
Cohesion: 0.09
Nodes (31): react, @react-three/fiber, three, BrainScene(), FirstFrameSignal(), KeyLight(), SCENE_BACKGROUND, BrainSurface() (+23 more)

### Community 5 - "App.jsx"
Cohesion: 0.09
Nodes (28): react-dom, App(), buildLookups(), computeRanks(), DEFAULT_SETTINGS, hasSeenIntro(), rememberIntroSeen(), CollapsibleSection() (+20 more)

### Community 6 - "package.json"
Cohesion: 0.10
Nodes (20): @react-three/drei, vite, @vitejs/plugin-react, dependencies, react, react-dom, @react-three/drei, @react-three/fiber (+12 more)

### Community 7 - "Step-by-Step Python Pipeline"
Cohesion: 0.13
Nodes (15): boto3 Dependency, braintwin Conda Environment, networkx Dependency, nibabel Dependency, BrainTwin Project, ConnectomeDB, HCP Credentials File (.hcp_credentials), HCP S3 Bucket (hcp-openaccess) (+7 more)

### Community 8 - "config.py"
Cohesion: 0.07
Nodes (19): load_fmri(), get_derived_dir(), get_run_name(), get_subject_dir(), get_use_gsr(), get_variant_suffix(), build_region_table(), load_region_colors() (+11 more)

## Knowledge Gaps
- **3 isolated node(s):** `#root Mount Div`, `RAW_DATA_DIR Config Setting`, `--run Scan Parameter (default rfMRI_REST1_LR)`
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 139 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `react` connect `NetworkLayer.jsx` to `App.jsx`, `package.json`?**
  _High betweenness centrality (0.044) - this node is a cross-community bridge._
- **What connects `#root Mount Div`, `RAW_DATA_DIR Config Setting`, `--run Scan Parameter (default rfMRI_REST1_LR)` to the rest of the system?**
  _3 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `numpy` be split into smaller, more focused modules?**
  _Cohesion score 0.05411392405063291 - nodes in this community are weakly interconnected._
- **Why does `Website HTML Entry Page` connect `Step-by-Step Python Pipeline` to `App.jsx`?**
  _High betweenness centrality (0.038) - this node is a cross-community bridge._
- **Should `step1_load_check.py` be split into smaller, more focused modules?**
  _Cohesion score 0.07678075855689177 - nodes in this community are weakly interconnected._
- **Should `step0_fetch_subject.py` be split into smaller, more focused modules?**
  _Cohesion score 0.10098522167487685 - nodes in this community are weakly interconnected._
- **Should `NetworkLayer.jsx` be split into smaller, more focused modules?**
  _Cohesion score 0.09191583610188261 - nodes in this community are weakly interconnected._