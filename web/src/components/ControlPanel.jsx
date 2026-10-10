import InfoTip from './InfoTip.jsx'
import {
  GLOSSARY, NETWORK_DESCRIPTIONS, SECONDS_PER_TIMEPOINT, describeModularity, describeMotion,
} from '../utils/explanations.js'

// Left panel: what this is, display switches, the connection-strength slider, and the
// network legend - all in everyday language.
// Inputs: subject, networks, settings + updateSetting(name, value), hiddenNetworks,
//         toggleNetwork(id), setAllNetworksVisible(bool), regionCounts (network -> count),
//         shownEdgeCount, graphThreshold (weakest r in the top-10% set), onOpenIntro().
// Output: an <aside> element.
export default function ControlPanel({
  subject, networks, settings, updateSetting, hiddenNetworks, toggleNetwork, setAllNetworksVisible,
  regionCounts, shownEdgeCount, graphThreshold, onOpenIntro,
}) {
  const motion = subject.qc.mean_relative_motion_mm
  const modularity = subject.graph_summary.modularity_schaefer_networks
  const scanMinutes = Math.round((subject.counts.timepoints * SECONDS_PER_TIMEPOINT) / 60)

  return (
    <aside className="panel control-panel">
      <header className="panel-header">
        <div className="title-row">
          <h1>BrainTwin</h1>
          <button type="button" className="help-button" onClick={onOpenIntro} aria-label="What am I looking at?"
            title="What am I looking at?">
            ?
          </button>
        </div>
        <p>One real person's brain, at rest</p>
        <p className="muted small">
          Human Connectome Project · subject {subject.hcp_id} · {scanMinutes}-minute resting scan
        </p>

        <p className="caption small">
          <span className="caption-term">
            Modularity {modularity.toFixed(2)}
            <InfoTip label="modularity" text={GLOSSARY.modularity} />
          </span>{' '}
          {describeModularity(modularity)}
        </p>
        <p className="caption small">
          <span className="caption-term">
            Head movement {motion.toFixed(2)} mm
            <InfoTip label="head motion" text={GLOSSARY.headMotion} />
          </span>{' '}
          The person kept {describeMotion(motion)}.
        </p>
      </header>

      <section>
        <h2>Brain surface</h2>
        <label className="switch-row">
          <input type="checkbox" checked={settings.showSurface}
            onChange={(event) => updateSetting('showSurface', event.target.checked)} />
          Show the brain's surface
        </label>
        <label className="switch-row">
          <input type="checkbox" checked={settings.surfaceColorMode === 'network'}
            disabled={!settings.showSurface}
            onChange={(event) => updateSetting('surfaceColorMode', event.target.checked ? 'network' : 'plain')} />
          Paint the surface in network colors
        </label>
        <label className="slider-row">
          <span>
            How solid the surface looks <span className="value">{Math.round(settings.surfaceOpacity * 100)}%</span>
          </span>
          <input type="range" min="0.05" max="1" step="0.05" value={settings.surfaceOpacity}
            aria-label="How solid the surface looks"
            disabled={!settings.showSurface}
            onChange={(event) => updateSetting('surfaceOpacity', Number(event.target.value))} />
        </label>
      </section>

      <section>
        <h2>Regions and connections</h2>
        <label className="switch-row">
          <input type="checkbox" checked={settings.showNetwork}
            onChange={(event) => updateSetting('showNetwork', event.target.checked)} />
          Show regions (balls) and connections (lines)
        </label>
        <div className="slider-row">
          <span>
            <label htmlFor="strength-slider">Only show connections this strong or stronger</label>
            <InfoTip label="connection strength" text={GLOSSARY.connectionStrength} />
          </span>
          <span className="slider-with-value">
            <input id="strength-slider" type="range" min="0.1" max="0.9" step="0.01" value={settings.edgeThreshold}
              disabled={!settings.showNetwork}
              onChange={(event) => updateSetting('edgeThreshold', Number(event.target.value))} />
            <span className="value">{settings.edgeThreshold.toFixed(2)}</span>
          </span>
          <span className="muted small slider-ends"><span>← more lines</span><span>fewer, stronger →</span></span>
        </div>
        <p className="muted small slider-note">
          {shownEdgeCount.toLocaleString()} connections shown ·{' '}
          <button type="button" className="link-button" disabled={!settings.showNetwork}
            onClick={() => updateSetting('edgeThreshold', graphThreshold)}>
            show the strongest 10% (used for the region stats)
          </button>
        </p>
        <label className="select-row">
          Ball size shows
          <select value={settings.nodeSizeBy} disabled={!settings.showNetwork}
            onChange={(event) => updateSetting('nodeSizeBy', event.target.value)}>
            <option value="uniform">Nothing (all the same)</option>
            <option value="strength">Total link strength</option>
            <option value="degree">Number of strong links</option>
            <option value="betweenness">Hub score</option>
            <option value="eigenvector">Influence</option>
          </select>
        </label>
      </section>

      <section>
        <div className="section-title-row">
          <h2>Brain networks</h2>
          <span className="small">
            <button type="button" className="link-button" onClick={() => setAllNetworksVisible(true)}>show all</button>
            {' · '}
            <button type="button" className="link-button" onClick={() => setAllNetworksVisible(false)}>hide all</button>
          </span>
        </div>
        <p className="muted small">Tick a network to show or hide its regions.</p>
        <ul className="legend">
          {networks.map((network) => {
            const visible = !hiddenNetworks.has(network.id)
            return (
              <li key={network.id}>
                <label className={visible ? '' : 'is-hidden'}>
                  <input type="checkbox" checked={visible} onChange={() => toggleNetwork(network.id)} />
                  <span className="swatch" style={{ background: network.color }} />
                  <span className="legend-text">
                    <span className="legend-name">
                      {network.name} <span className="muted small">· {regionCounts[network.id]} regions</span>
                    </span>
                    <span className="legend-description">{NETWORK_DESCRIPTIONS[network.id]}</span>
                  </span>
                </label>
              </li>
            )
          })}
        </ul>
      </section>

      <footer className="muted small help">
        Drag to turn the brain · scroll to zoom · right-drag to move it · use the view buttons at the bottom ·
        click a ball or the surface to learn about a region · Esc to clear
      </footer>
    </aside>
  )
}
