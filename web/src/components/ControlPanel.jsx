// Left panel: subject info, layer switches, edge threshold slider, and the network legend.
// Inputs: subject, networks, settings + updateSetting(name, value), hiddenNetworks,
//         toggleNetwork(id), setAllNetworksVisible(bool), regionCounts (network -> count),
//         shownEdgeCount, graphThreshold (weakest r in the 10% graph).
// Output: an <aside> element.
export default function ControlPanel({
  subject, networks, settings, updateSetting, hiddenNetworks, toggleNetwork, setAllNetworksVisible,
  regionCounts, shownEdgeCount, graphThreshold,
}) {
  const run = subject.run_name.replace('rfMRI_', '')
  const motion = subject.qc.mean_relative_motion_mm

  return (
    <aside className="panel control-panel">
      <header className="panel-header">
        <h1>BrainTwin</h1>
        <p className="muted">
          {subject.subject_id} · HCP {subject.hcp_id} · {run}
        </p>
        <p className="muted small">
          Schaefer 200 regions · head motion {motion.toFixed(3)} mm · modularity{' '}
          {subject.graph_summary.modularity_schaefer_networks.toFixed(2)}
        </p>
      </header>

      <section>
        <h2>Brain surface</h2>
        <label className="switch-row">
          <input type="checkbox" checked={settings.showSurface}
            onChange={(event) => updateSetting('showSurface', event.target.checked)} />
          Show surface
        </label>
        <label className="switch-row">
          <input type="checkbox" checked={settings.surfaceColorMode === 'network'}
            disabled={!settings.showSurface}
            onChange={(event) => updateSetting('surfaceColorMode', event.target.checked ? 'network' : 'plain')} />
          Color surface by network
        </label>
        <label className="slider-row">
          <span>Opacity <span className="value">{Math.round(settings.surfaceOpacity * 100)}%</span></span>
          <input type="range" min="0.05" max="1" step="0.05" value={settings.surfaceOpacity}
            aria-label="Surface opacity"
            disabled={!settings.showSurface}
            onChange={(event) => updateSetting('surfaceOpacity', Number(event.target.value))} />
        </label>
      </section>

      <section>
        <h2>Network layer</h2>
        <label className="switch-row">
          <input type="checkbox" checked={settings.showNetwork}
            onChange={(event) => updateSetting('showNetwork', event.target.checked)} />
          Show nodes and connections
        </label>
        <label className="slider-row">
          <span>
            Connection strength r ≥ <span className="value">{settings.edgeThreshold.toFixed(2)}</span>
          </span>
          <input type="range" min="0.1" max="0.9" step="0.01" value={settings.edgeThreshold}
            aria-label="Minimum connection strength"
            disabled={!settings.showNetwork}
            onChange={(event) => updateSetting('edgeThreshold', Number(event.target.value))} />
        </label>
        <p className="muted small slider-note">
          {shownEdgeCount.toLocaleString()} connections shown ·{' '}
          <button type="button" className="link-button" disabled={!settings.showNetwork}
            onClick={() => updateSetting('edgeThreshold', graphThreshold)}>
            use 10% graph cutoff (r ≥ {graphThreshold.toFixed(2)})
          </button>
        </p>
        <label className="select-row">
          Node size
          <select value={settings.nodeSizeBy} disabled={!settings.showNetwork}
            onChange={(event) => updateSetting('nodeSizeBy', event.target.value)}>
            <option value="uniform">Same size</option>
            <option value="strength">Strength</option>
            <option value="degree">Degree</option>
            <option value="betweenness">Betweenness</option>
            <option value="eigenvector">Eigenvector</option>
          </select>
        </label>
      </section>

      <section>
        <div className="section-title-row">
          <h2>Networks</h2>
          <span className="small">
            <button type="button" className="link-button" onClick={() => setAllNetworksVisible(true)}>all</button>
            {' · '}
            <button type="button" className="link-button" onClick={() => setAllNetworksVisible(false)}>none</button>
          </span>
        </div>
        <ul className="legend">
          {networks.map((network) => {
            const visible = !hiddenNetworks.has(network.id)
            return (
              <li key={network.id}>
                <label className={visible ? '' : 'is-hidden'}>
                  <input type="checkbox" checked={visible} onChange={() => toggleNetwork(network.id)} />
                  <span className="swatch" style={{ background: network.color }} />
                  <span className="legend-name">{network.name}</span>
                  <span className="muted small">{regionCounts[network.id]}</span>
                </label>
              </li>
            )
          })}
        </ul>
      </section>

      <footer className="muted small help">
        Drag to rotate · scroll to zoom · right-drag to pan · click a node or the surface to inspect a
        region · Esc to clear
      </footer>
    </aside>
  )
}
