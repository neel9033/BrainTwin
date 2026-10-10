import { STATS, hemisphereName, regionTitle } from '../utils/regions.js'

// Right panel with details for the selected region.
// Inputs: node (selected region), nodesById, networkNames, networkColors,
//         ranks (stat -> Map id -> rank), regionTotal, graphThreshold,
//         onSelect(id) to jump to a partner, onClose().
// Output: an <aside> element.
export default function SidePanel({
  node, nodesById, networkNames, networkColors, ranks, regionTotal, graphThreshold, onSelect, onClose,
}) {
  const isIsolated = node.stats.degree === 0
  const strongestWeight = node.top_connections[0]?.weight || 1

  return (
    <aside className="panel side-panel">
      <header className="panel-header side-header">
        <div>
          <p className="eyebrow">
            <span className="swatch" style={{ background: networkColors[node.network] }} />
            {networkNames[node.network]} · {hemisphereName(node.hemisphere)}
          </p>
          <h2 className="region-title">{regionTitle(node, networkNames)}</h2>
          <p className="muted small mono">{node.full_name}</p>
          <p className="muted small">
            Region {node.id} · {node.vertex_count} surface vertices
          </p>
        </div>
        <button type="button" className="close-button" onClick={onClose} aria-label="Close panel">
          ×
        </button>
      </header>

      <section>
        <h3>Graph statistics</h3>
        {isIsolated && (
          <p className="note small">
            No connections strong enough for the 10% graph, so these are all 0. Its strongest partners from
            the full matrix are listed below.
          </p>
        )}
        <table className="stats-table">
          <tbody>
            {STATS.map((stat) => {
              const rank = ranks[stat.key].get(node.id)
              const percentile = 1 - (rank - 1) / (regionTotal - 1)
              return (
                <tr key={stat.key} title={stat.help}>
                  <th scope="row">{stat.label}</th>
                  <td className="number">{node.stats[stat.key].toFixed(stat.digits)}</td>
                  <td className="rank-cell">
                    <span className="rank-bar"><span style={{ width: `${percentile * 100}%` }} /></span>
                    <span className="muted small">#{rank}</span>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
        <p className="muted small">Rank out of {regionTotal} regions. Hover a row for what it means.</p>
      </section>

      <section>
        <h3>Strongest connections</h3>
        <ol className="connection-list">
          {node.top_connections.map((connection) => {
            const partner = nodesById.get(connection.id)
            return (
              <li key={connection.id}>
                <button type="button" onClick={() => onSelect(partner.id)}>
                  <span className="swatch" style={{ background: networkColors[partner.network] }} />
                  <span className="connection-name">
                    {regionTitle(partner, networkNames)}
                    <span className="muted small"> · {partner.hemisphere}</span>
                  </span>
                  <span className="connection-bar">
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
          Pearson r from the full matrix. Grey values are below the 10% graph cutoff (r &lt;{' '}
          {graphThreshold.toFixed(2)}). Click a partner to jump to it.
        </p>
      </section>
    </aside>
  )
}
