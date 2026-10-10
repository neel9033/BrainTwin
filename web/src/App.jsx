import { useEffect, useMemo, useState } from 'react'
import { loadSubject } from './data/loadSubject.js'
import { STATS } from './utils/regions.js'
import BrainScene from './components/BrainScene.jsx'
import ControlPanel from './components/ControlPanel.jsx'
import SidePanel from './components/SidePanel.jsx'
import ViewBar from './components/ViewBar.jsx'

const SUBJECT_ID = 'subject_001'

const DEFAULT_SETTINGS = {
  showSurface: true,
  surfaceOpacity: 0.3,
  surfaceColorMode: 'plain', // "plain" or "network"
  showNetwork: true,
  edgeThreshold: 0.5,
  nodeSizeBy: 'strength',
}

// Rank every region for each statistic (1 = highest; ties share a rank).
// Input: nodes. Output: { statKey: Map(region id -> rank) }
function computeRanks(nodes) {
  const ranks = {}
  for (const { key } of STATS) {
    const values = nodes.map((node) => node.stats[key])
    ranks[key] = new Map(
      nodes.map((node) => [node.id, 1 + values.filter((value) => value > node.stats[key]).length]),
    )
  }
  return ranks
}

// Look-up tables built once from the loaded data.
// Input: data from loadSubject. Output: object of maps/numbers used across the app.
function buildLookups(data) {
  const { nodes, edges, networks } = data.graph
  const regionCounts = {}
  nodes.forEach((node) => {
    regionCounts[node.network] = (regionCounts[node.network] || 0) + 1
  })
  const graphEdgeWeights = edges.filter((edge) => edge.in_graph).map((edge) => edge.weight)
  return {
    nodesById: new Map(nodes.map((node) => [node.id, node])),
    networkColors: Object.fromEntries(networks.map((network) => [network.id, network.color])),
    networkNames: Object.fromEntries(networks.map((network) => [network.id, network.name])),
    regionCounts,
    ranks: computeRanks(nodes),
    graphThreshold: Math.min(...graphEdgeWeights), // weakest r kept in the 10% graph
  }
}

// The whole app: loads the subject, keeps the view settings and selection,
// and lays out the controls, 3D view, and detail panel.
export default function App() {
  const [data, setData] = useState(null)
  const [loadError, setLoadError] = useState(null)
  const [settings, setSettings] = useState(DEFAULT_SETTINGS)
  const [hiddenNetworks, setHiddenNetworks] = useState(() => new Set())
  const [selectedId, setSelectedId] = useState(null)
  const [notice, setNotice] = useState(null)
  const [autoRotate, setAutoRotate] = useState(true)
  const [viewRequest, setViewRequest] = useState(null) // { name, id } for the camera presets

  useEffect(() => {
    loadSubject(SUBJECT_ID).then(setData).catch((error) => setLoadError(error.message))
  }, [])

  // Esc clears the selection
  useEffect(() => {
    function handleKey(event) {
      if (event.key === 'Escape') setSelectedId(null)
    }
    window.addEventListener('keydown', handleKey)
    return () => window.removeEventListener('keydown', handleKey)
  }, [])

  // Auto-rotate stops on any user interaction: a click or touch anywhere, scrolling, or a key
  useEffect(() => {
    if (!autoRotate) return undefined
    const stop = () => setAutoRotate(false)
    const events = ['pointerdown', 'wheel', 'keydown']
    events.forEach((name) => window.addEventListener(name, stop))
    return () => events.forEach((name) => window.removeEventListener(name, stop))
  }, [autoRotate])

  // Hide the "medial wall" notice after a few seconds
  useEffect(() => {
    if (!notice) return undefined
    const timer = setTimeout(() => setNotice(null), 2500)
    return () => clearTimeout(timer)
  }, [notice])

  const lookups = useMemo(() => (data ? buildLookups(data) : null), [data])

  const visibleNodes = useMemo(
    () => (data ? data.graph.nodes.filter((node) => !hiddenNetworks.has(node.network)) : []),
    [data, hiddenNetworks],
  )

  // Edges to draw: above the slider value and both ends in a visible network.
  // (When a region is selected, the network layer fades the ones that don't touch it.)
  const visibleEdges = useMemo(() => {
    if (!data) return []
    const visibleIds = new Set(visibleNodes.map((node) => node.id))
    return data.graph.edges.filter(
      (edge) => edge.weight >= settings.edgeThreshold && visibleIds.has(edge.source) && visibleIds.has(edge.target),
    )
  }, [data, visibleNodes, settings.edgeThreshold])

  // The selected region's own visible connections
  const selectedEdges = useMemo(
    () =>
      selectedId == null
        ? []
        : visibleEdges.filter((edge) => edge.source === selectedId || edge.target === selectedId),
    [visibleEdges, selectedId],
  )

  // The selected region plus every partner it has a visible line to
  const highlightedIds = useMemo(() => {
    const ids = new Set(selectedId != null ? [selectedId] : [])
    selectedEdges.forEach((edge) => {
      ids.add(edge.source)
      ids.add(edge.target)
    })
    return ids
  }, [selectedEdges, selectedId])

  // Update one view setting by name
  function updateSetting(name, value) {
    setSettings((current) => ({ ...current, [name]: value }))
  }

  // Show or hide one network
  function toggleNetwork(networkId) {
    setHiddenNetworks((current) => {
      const next = new Set(current)
      if (next.has(networkId)) next.delete(networkId)
      else next.add(networkId)
      return next
    })
  }

  // Show (true) or hide (false) every network at once
  function setAllNetworksVisible(visible) {
    setHiddenNetworks(visible ? new Set() : new Set(data.graph.networks.map((network) => network.id)))
  }

  // Move the camera to a preset view (a new id each time, so pressing the same view again still works)
  function showView(name) {
    setViewRequest({ name, id: Date.now() })
  }

  // A click on the surface: region 0 is the medial wall, which has no region
  function handleSurfaceClick(regionId) {
    if (regionId === 0) {
      setSelectedId(null)
      setNotice('That spot is the medial wall, which has no region.')
    } else {
      setSelectedId(regionId)
    }
  }

  if (loadError) {
    return (
      <div className="status-screen">
        <h1>Couldn't load the brain data</h1>
        <p>{loadError}</p>
      </div>
    )
  }
  if (!data) {
    return (
      <div className="status-screen">
        <p className="muted">Loading {SUBJECT_ID}…</p>
      </div>
    )
  }

  const selectedNode = selectedId != null ? lookups.nodesById.get(selectedId) : null

  return (
    <div className="app">
      <div className="scene">
        <BrainScene
          data={data}
          nodesById={lookups.nodesById}
          networkColors={lookups.networkColors}
          networkNames={lookups.networkNames}
          settings={settings}
          hiddenNetworks={hiddenNetworks}
          visibleNodes={visibleNodes}
          visibleEdges={visibleEdges}
          selectedId={selectedId}
          highlightedIds={highlightedIds}
          onSelect={setSelectedId}
          onSurfaceClick={handleSurfaceClick}
          viewRequest={viewRequest}
          autoRotate={autoRotate}
          onUserInteract={() => setAutoRotate(false)}
        />
      </div>

      <ViewBar onView={showView} autoRotate={autoRotate} onToggleAutoRotate={() => setAutoRotate((on) => !on)} />

      <ControlPanel
        subject={data.subject}
        networks={data.graph.networks}
        settings={settings}
        updateSetting={updateSetting}
        hiddenNetworks={hiddenNetworks}
        toggleNetwork={toggleNetwork}
        setAllNetworksVisible={setAllNetworksVisible}
        regionCounts={lookups.regionCounts}
        shownEdgeCount={selectedId != null ? selectedEdges.length : visibleEdges.length}
        graphThreshold={lookups.graphThreshold}
      />

      {selectedNode && (
        <SidePanel
          node={selectedNode}
          nodesById={lookups.nodesById}
          networkNames={lookups.networkNames}
          networkColors={lookups.networkColors}
          ranks={lookups.ranks}
          regionTotal={data.graph.nodes.length}
          graphThreshold={lookups.graphThreshold}
          onSelect={setSelectedId}
          onClose={() => setSelectedId(null)}
        />
      )}

      {notice && <div className="notice">{notice}</div>}
    </div>
  )
}
