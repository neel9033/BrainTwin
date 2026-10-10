// Small helpers for showing regions and stats in plain language.

// Graph statistics shown in the side panel, with a plain-language explanation.
export const STATS = [
  { key: 'degree', label: 'Degree', digits: 0,
    help: 'How many connections this region has in the strongest-10% graph.' },
  { key: 'strength', label: 'Strength', digits: 2,
    help: 'Sum of the correlation values of those connections.' },
  { key: 'betweenness', label: 'Betweenness', digits: 3,
    help: 'How often this region lies on the shortest path between two other regions (a "bridge" score).' },
  { key: 'clustering', label: 'Clustering', digits: 3,
    help: "How strongly this region's partners are also connected to each other." },
  { key: 'eigenvector', label: 'Eigenvector', digits: 3,
    help: 'High when a region is connected to other well-connected regions.' },
]

// Readable title for a region.
// Input: node from graph.json (e.g. name "SalVentAttn_TempOccPar_3").
// Output: string like "TempOccPar 3", or "Visual 13" when there's no sub-area name.
export function regionTitle(node, networkNames) {
  const parts = node.name.split('_').slice(1) // drop the network part
  if (parts.length === 1) return `${networkNames[node.network]} ${parts[0]}`
  return parts.join(' ')
}

// Input: "L" or "R". Output: "Left hemisphere" / "Right hemisphere".
export function hemisphereName(hemisphere) {
  return hemisphere === 'L' ? 'Left hemisphere' : 'Right hemisphere'
}

// Convert "#rrggbb" to [r, g, b] with values 0..1 (what WebGL colors use).
export function hexToRgb(hex) {
  const value = parseInt(hex.slice(1), 16)
  return [((value >> 16) & 255) / 255, ((value >> 8) & 255) / 255, (value & 255) / 255]
}

// Blend two [r, g, b] colors. amount = 0 gives first, 1 gives second.
export function mixRgb(first, second, amount) {
  return first.map((channel, index) => channel + (second[index] - channel) * amount)
}
