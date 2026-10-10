// Loads one subject's exported files (written by pipeline/step6_export_web.py)
// from web/public/data/<subjectId>/ and turns them into ready-to-use objects.

// Fetch a file and fail with a helpful message if it's missing.
// Input: url string. Output: the fetch Response.
async function fetchOrExplain(url) {
  const response = await fetch(url)
  const contentType = response.headers.get('content-type') || ''
  // The Vite dev server answers missing files with index.html, so check for that too
  if (!response.ok || contentType.includes('text/html')) {
    throw new Error(
      `Could not load ${url}. Run the pipeline first (steps 1-6, ending with ` +
        `pipeline/step6_export_web.py) so the data files exist.`,
    )
  }
  return response
}

// Load a raw binary array file.
// Inputs: url, ArrayType (e.g. Float32Array). Output: typed array.
async function fetchBinary(url, ArrayType) {
  const response = await fetchOrExplain(url)
  return new ArrayType(await response.arrayBuffer())
}

// Load everything the viewer needs for one subject.
// Input: subjectId like "subject_001".
// Output: { subject, graph, meshes: { L: { points, triangles, regions }, R: {...} } }
//   points: Float32Array (x,y,z per vertex), triangles: Uint32Array (3 per triangle),
//   regions: Uint16Array (region id per vertex, 0 = medial wall)
export async function loadSubject(subjectId) {
  const folder = `${import.meta.env.BASE_URL}data/${subjectId}/`

  const [subject, graph] = await Promise.all([
    fetchOrExplain(folder + 'subject.json').then((response) => response.json()),
    fetchOrExplain(folder + 'graph.json').then((response) => response.json()),
  ])

  const meshes = {}
  for (const hemisphere of ['L', 'R']) {
    const [points, triangles, regions] = await Promise.all([
      fetchBinary(`${folder}mesh_${hemisphere}_points.bin`, Float32Array),
      fetchBinary(`${folder}mesh_${hemisphere}_triangles.bin`, Uint32Array),
      fetchBinary(`${folder}mesh_${hemisphere}_region.bin`, Uint16Array),
    ])
    meshes[hemisphere] = { points, triangles, regions }
  }

  return { subject, graph, meshes }
}
