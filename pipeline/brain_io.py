"""
Shared loading helpers used by several pipeline steps.

These functions only read files and reshape them into simple numpy arrays.
They never write anything.
"""

import nibabel as nib
import numpy as np

# Names nibabel uses for the two cortical surfaces inside a CIFTI file
CORTEX_STRUCTURES = {
    "L": "CIFTI_STRUCTURE_CORTEX_LEFT",
    "R": "CIFTI_STRUCTURE_CORTEX_RIGHT",
}


def load_mesh(mesh_path):
    """
    Load a GIFTI surface mesh.
    Input: path to a .surf.gii file.
    Output: (brain_points, triangles)
            brain_points: float array (n_vertices, 3) of x, y, z in mm
            triangles: int array (n_triangles, 3) of vertex indices
    """
    gifti = nib.load(str(mesh_path))
    brain_points = gifti.agg_data("NIFTI_INTENT_POINTSET")
    triangles = gifti.agg_data("NIFTI_INTENT_TRIANGLE")
    return np.asarray(brain_points), np.asarray(triangles)


def get_cortex_columns(brain_model_axis, hemisphere):
    """
    Find which CIFTI columns belong to one hemisphere's cortex, and which
    surface vertex each of those columns represents.
    Inputs: brain_model_axis (nibabel BrainModelAxis), hemisphere ("L" or "R").
    Output: (column_indices, vertex_indices) - two int arrays of equal length.
            column_indices[i] is a column in the CIFTI data;
            vertex_indices[i] is the mesh vertex that column belongs to.
    """
    structure_name = CORTEX_STRUCTURES[hemisphere]
    for name, column_slice, sub_axis in brain_model_axis.iter_structures():
        if name == structure_name:
            column_indices = np.arange(column_slice.start, column_slice.stop or len(brain_model_axis))
            vertex_indices = np.asarray(sub_axis.vertex)
            return column_indices, vertex_indices
    raise ValueError(f"{structure_name} not found in CIFTI file")


def load_fmri(fmri_path):
    """
    Load a resting-state CIFTI dense time series.
    Input: path to a .dtseries.nii file.
    Output: (fmri_data, brain_model_axis, series_axis)
            fmri_data: float32 array (timepoints, grayordinates)
            brain_model_axis: tells which vertex/voxel each column is
            series_axis: timing information for the rows
    """
    cifti = nib.load(str(fmri_path))
    fmri_data = cifti.get_fdata(dtype=np.float32)
    series_axis = cifti.header.get_axis(0)
    brain_model_axis = cifti.header.get_axis(1)
    return fmri_data, brain_model_axis, series_axis


def load_atlas(atlas_path, vertices_per_hemisphere):
    """
    Load the Schaefer dlabel atlas and spread its labels onto full
    hemisphere vertex arrays (so index = mesh vertex index).
    Inputs: atlas_path (.dlabel.nii), vertices_per_hemisphere (32492).
    Output: (vertex_labels, label_table)
            vertex_labels: dict {"L": int array (32492,), "R": int array (32492,)}
                           with the region id of every vertex (0 = no region / medial wall)
            label_table: dict {region_id: region_full_name}, excluding id 0
    """
    cifti = nib.load(str(atlas_path))
    atlas_values = np.asarray(cifti.get_fdata()).ravel().astype(int)
    label_axis = cifti.header.get_axis(0)
    brain_model_axis = cifti.header.get_axis(1)

    vertex_labels = {}
    for hemisphere in ("L", "R"):
        column_indices, vertex_indices = get_cortex_columns(brain_model_axis, hemisphere)
        full_labels = np.zeros(vertices_per_hemisphere, dtype=int)
        full_labels[vertex_indices] = atlas_values[column_indices]
        vertex_labels[hemisphere] = full_labels

    label_table = {
        region_id: name
        for region_id, (name, _color) in label_axis.label[0].items()
        if region_id != 0
    }
    return vertex_labels, label_table


def parse_region_name(full_name):
    """
    Split a Schaefer parcel name into its parts.
    Input: e.g. "7Networks_LH_DorsAttn_Post_1"
    Output: dict with hemisphere ("L"/"R"), network ("DorsAttn"),
            region_name ("DorsAttn_Post_1")
    """
    parts = full_name.split("_")  # ["7Networks", "LH", "DorsAttn", "Post", "1"]
    hemisphere = {"LH": "L", "RH": "R"}[parts[1]]
    network = parts[2]
    region_name = "_".join(parts[2:])
    return {"hemisphere": hemisphere, "network": network, "region_name": region_name}
