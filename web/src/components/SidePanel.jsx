import CollapsibleSection from './CollapsibleSection.jsx'
import InfoTip from './InfoTip.jsx'
import { STATS, hemisphereName, regionTitle } from '../utils/regions.js'
import { GLOSSARY, NETWORK_DESCRIPTIONS, describeStat } from '../utils/explanations.js'

// Right panel with details for the selected region. Each statistic is explained in
// a plain sentence first, with the number and its rank underneath.
// Inputs: node (selected region), nodesById, networkNames, networkColors,
//         ranks (stat -> Map id -> rank), regionTotal, graphThreshold,
//         onSelect(id) to jump to a partner, onClose().
// Output: an <aside> element.
export default function SidePanel({
  node, nodesById, networkNames, networkColors, ranks, regionTotal, graphThreshold, onSelect, onClose,
}) {
  const hasLinks = node.stats.degree > 0
  const strongestWeight = node.top_connections[0]?.weight || 1

  return (
    <aside className="panel side-panel">
      <header className="panel-header side-header">
        <div>
          <p className="eyebrow">
            <span className="swatch" style={{ background: networkColors[node.network] }} />
            {networkNames[node.network]} network · {hemisphereName(node.hemisphere)}
          </p>
          <h2 className="region-title">{regionTitle(node, networkNames)}</h2>
          <p className="muted small">{NETWORK_DESCRIPTIONS[node.network]}</p>
          <p className="muted small mono">
            Region {node.id} · {node.full_name}
          </p>
        </div>
        <button type="button" className="close-button" onClick={onClose} aria-label="Close panel">
          ×
        </button>
      </header>

      <CollapsibleSection title="How it fits into the network">
        {!hasLinks && (
          <p className="note small">
            None of this region's connections are among the strongest 10%, so the measures below are all zero.
            This often happens where the scan signal is weak. Its closest partners are still listed further down.
          </p>
        )}
        <ul className="stat-list">
          {STATS.map((stat) => {
            const value = node.stats[stat.key]
            const rank = ranks[stat.key].get(node.id)
            const percentile = 1 - (rank - 1) / (regionTotal - 1)
            const { label, sentence } = describeStat(stat.key, value, rank, regionTotal, hasLinks)
            return (
              <li key={stat.key} className="stat">
                <p className="stat-sentence">{sentence}</p>
                <div className="stat-figure">
                  <span className="stat-label">
                    {label}
                    {stat.key === 'betweenness' && <InfoTip label="a hub" text={GLOSSARY.hub} />}
                  </span>
                  <span className="number">{value.toFixed(stat.digits)}</span>
                  <span className="rank-text">#{rank}</span>
                  <span className="rank-bar" aria-hidden="true">
                    <span style={{ width: `${percentile * 100}%` }} />
                  </span>
                </div>
              </li>
            )
          })}
        </ul>
        <p className="muted small">
          Measured on the strongest 10% of connections. # is the rank among all {regionTotal} regions (#1 =
          highest); the bar shows the same thing.
        </p>
      </CollapsibleSection>

      <CollapsibleSection
        title={
          <>
            Regions most in sync with this one
            <InfoTip label="connection strength" text={GLOSSARY.connectionStrength} />
          </>
        }
      >
        <ol className="connection-list">
          {node.top_connections.map((connection) => {
            const partner = nodesById.get(connection.id)
            return (
              <li key={connection.id}>
                <button type="button" onClick={() => onSelect(partner.id)}>
                  <span className="swatch" style={{ background: networkColors[partner.network] }} />
                  <span className="connection-name">
                    {regionTitle(partner, networkNames)}
                    <span className="muted small"> · {partner.hemisphere === 'L' ? 'left' : 'right'}</span>
                  </span>
                  <span className="connection-bar" aria-hidden="true">
                    <span style={{ width: `${Math.max(0, connection.weight / strongestWeight) * 100}%` }} />
                  </span>
                  <span className={`number ${connection.weight >= graphThreshold ? '' : 'muted'}`}>
                    {connection.weight.toFixed(2)}
                  </span>
                </button>
              </li>
            )
          })}
        </ol>
        <p className="muted small">
          Higher numbers mean their activity rose and fell together more closely (1 = perfectly in step). Grey
          numbers are below the strongest-10% cutoff. Click a region to jump to it.
        </p>
      </CollapsibleSection>
    </aside>
  )
}
