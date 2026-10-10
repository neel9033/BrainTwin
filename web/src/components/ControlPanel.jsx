import CollapsibleSection from './CollapsibleSection.jsx'
import InfoTip from './InfoTip.jsx'
import ReproducibilityScatter from './ReproducibilityScatter.jsx'
import {
  GLOSSARY, NETWORK_DESCRIPTIONS, SECONDS_PER_TIMEPOINT, describeModularity, describeMotion,
  describeReproducibility,
} from '../utils/explanations.js'

// Left panel: what this is, which scan is shown, how well the two scans agree,
// display switches, the connection-strength slider, and the network legend -
// all in everyday language.
// Inputs: subject, runInfo (scan on screen), runLabels + runLabel + onRunChange(label),
//         comparison ({ summary, pairValues } or null), selectedId, nodesById, networks,
//         settings + updateSetting(name, value), hiddenNetworks, toggleNetwork(id),
//         setAllNetworksVisible(bool), regionCounts (network -> count), shownEdgeCount,
//         graphThreshold (weakest r in the top-10% set), onOpenIntro().
// Output: an <aside> element.
export default function ControlPanel({
  subject, runInfo, runLabels, runLabel, onRunChange, comparison, selectedId, nodesById, networks,
  settings, updateSetting, hiddenNetworks, toggleNetwork, setAllNetworksVisible,
  regionCounts, shownEdgeCount, graphThreshold, onOpenIntro,
}) {
  const motion = runInfo.qc.mean_relative_motion_mm
  const modularity = runInfo.graph_summary.modularity_schaefer_networks
  const scanMinutes = Math.round((runInfo.timepoints * SECONDS_PER_TIMEPOINT) / 60)
  const scanNumber = runLabels.indexOf(runLabel) + 1
  const agreement = comparison?.summary.matrix_correlation
  const nodesInOrder = [...nodesById.values()].sort((first, second) => first.id - second.id)

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
        <p className="subtitle">One real person's brain, at rest</p>
        <p className="muted small">
          Human Connectome Project · subject {subject.hcp_id} · {scanMinutes}-minute resting scan
        </p>

        {runLabels.length > 1 && (
          <div className="run-switcher">
            <div className="segmented" role="group" aria-label="Which scan to show">
              {runLabels.map((label) => (
                <button key={label} type="button" aria-pressed={label === runLabel}
                  className={label === runLabel ? 'is-on' : ''} onClick={() => onRunChange(label)}>
                  {label}
                </button>
              ))}
            </div>
            <span className="muted small">Day {scanNumber} of {runLabels.length}</span>
          </div>
        )}

        {agreement != null && (
          <p className="caption small">
            <span className="caption-term">
              Reproducibility {agreement.toFixed(2)}
              <InfoTip label="reproducibility" text={GLOSSARY.reproducibility} />
            </span>{' '}
            {describeReproducibility(agreement)}
          </p>
        )}
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

      {comparison && (
        <CollapsibleSection title="Same brain, two scans">
          <p className="small">
            Each dot is one connection between two regions. Dots near the diagonal line mean the two scans
            agree.
          </p>
          <ReproducibilityScatter
            pairValues={comparison.pairValues}
            nodes={nodesInOrder}
            networkNames={Object.fromEntries(networks.map((network) => [network.id, network.name]))}
            runLabels={comparison.summary.run_labels}
            selectedId={selectedId}
          />
          <table className="compare-table small">
            <thead>
              <tr>
                <th scope="col" />
                {comparison.summary.run_labels.map((label) => (
                  <th scope="col" key={label} className={label === runLabel ? 'is-current' : ''}>{label}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              <tr>
                <th scope="row">Head movement (mm)</th>
                {comparison.summary.run_labels.map((label) => (
                  <td key={label} className="number">{comparison.summary.head_motion_mm[label].toFixed(3)}</td>
                ))}
              </tr>
              <tr>
                <th scope="row">Modularity</th>
                {comparison.summary.run_labels.map((label) => (
                  <td key={label} className="number">{comparison.summary.modularity[label].toFixed(2)}</td>
                ))}
              </tr>
            </tbody>
          </table>
          <p className="muted small">
            {Math.round(comparison.summary.top10_edge_overlap * 100)}% of the strongest connections appear in
            both scans. Each region's total link strength agrees at r ={' '}
            {comparison.summary.strength_correlation.toFixed(2)} (
            {comparison.summary.strength_correlation_all_positive.toFixed(2)} when every positive connection is
            counted, not just the strongest).
          </p>
        </CollapsibleSection>
      )}

      <CollapsibleSection title="Brain surface">
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
      </CollapsibleSection>

      <CollapsibleSection title="Regions and connections">
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
      </CollapsibleSection>

      <CollapsibleSection
        title="Brain networks"
        actions={
          <>
            <button type="button" className="link-button" onClick={() => setAllNetworksVisible(true)}>show all</button>
            <span aria-hidden="true"> · </span>
            <button type="button" className="link-button" onClick={() => setAllNetworksVisible(false)}>hide all</button>
          </>
        }
      >
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
      </CollapsibleSection>

      <footer className="muted small help">
        Drag to turn the brain · scroll to zoom · right-drag to move it · use the view buttons at the bottom ·
        click a ball or the surface to learn about a region · Esc to clear
      </footer>
    </aside>
  )
}
