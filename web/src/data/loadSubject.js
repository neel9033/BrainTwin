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

// Load everything the viewer needs for one subject, reporting progress as it goes.
// Inputs: subjectId like "subject_001";
//         onProgress({ fraction, label }) - optional, called as files arrive
//         (fraction 0..1, weighted by file size from subject.json).
// Output: {
//   subject,                       contents of subject.json
//   meshes: { L, R },              { points, triangles, regions } typed arrays per hemisphere
//   runs: { REST1: { info, graph }, REST2: {...} },   one graph per scan
//   comparison: { summary, pairValues } or null       reproducibility data, if exported
// }
//   points: Float32Array (x,y,z per vertex), triangles: Uint32Array (3 per triangle),
//   regions: Uint16Array (region id per vertex, 0 = medial wall),
//   pairValues: Float32Array of [r in run 1, r in run 2] for every region pair
export async function loadSubject(subjectId, onProgress = () => {}) {
  const folder = `${import.meta.env.BASE_URL}data/${subjectId}/`

  onProgress({ fraction: 0, label: 'Reading scan details' })
  const subject = await fetchOrExplain(folder + 'subject.json').then((response) => response.json())
  if (!subject.runs) {
    throw new Error('These data files are from an older version. Re-run pipeline/step6_export_web.py.')
  }

  // subject.json lists every other file and its size, so progress can be measured in bytes
  const sizes = Object.fromEntries(subject.files.map((file) => [file.file, file.bytes]))
  const totalBytes = Object.values(sizes).reduce((sum, bytes) => sum + bytes, 0)
  let loadedBytes = 0

  // Load one file, then record its progress. Output: parsed JSON or a typed array.
  async function load(fileName, ArrayType, label) {
    const response = await fetchOrExplain(folder + fileName)
    const result = ArrayType ? new ArrayType(await response.arrayBuffer()) : await response.json()
    loadedBytes += sizes[fileName] || 0
    onProgress({ fraction: loadedBytes / totalBytes, label })
    return result
  }

  onProgress({ fraction: 0, label: 'Loading brain surface and scans' })
  const meshPromises = ['L', 'R'].map(async (hemisphere) => {
    const side = hemisphere === 'L' ? 'left' : 'right'
    const [points, triangles, regions] = await Promise.all([
      load(`mesh_${hemisphere}_points.bin`, Float32Array, `${side} surface shape loaded`),
      load(`mesh_${hemisphere}_triangles.bin`, Uint32Array, `${side} surface triangles loaded`),
      load(`mesh_${hemisphere}_region.bin`, Uint16Array, `${side} region map loaded`),
    ])
    return [hemisphere, { points, triangles, regions }]
  })
  const runPromises = subject.runs.map(async (info) => {
    const graph = await load(info.graph_file, null, `${info.label} network loaded`)
    return [info.label, { info, graph }]
  })
  const comparisonPromise = subject.comparison
    ? Promise.all([
        load(subject.comparison.file, null, 'Scan comparison loaded'),
        load(subject.comparison.edges_file, Float32Array, 'Scan comparison loaded'),
      ]).then(([summary, pairValues]) => ({ summary, pairValues }))
    : Promise.resolve(null)

  const [meshEntries, runEntries, comparison] = await Promise.all([
    Promise.all(meshPromises),
    Promise.all(runPromises),
    comparisonPromise,
  ])

  return {
    subject,
    meshes: Object.fromEntries(meshEntries),
    runs: Object.fromEntries(runEntries),
    comparison,
  }
}
