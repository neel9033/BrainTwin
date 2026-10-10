// Plain-English text for people without a neuroscience background.
// All the explanatory wording lives here so it's easy to edit in one place.

// HCP-Young Adult resting-state scans take one picture of the brain every 0.72 seconds
export const SECONDS_PER_TIMEPOINT = 0.72

// One line per network: what it's known for
export const NETWORK_DESCRIPTIONS = {
  Vis: 'Processing what you see.',
  SomMot: 'Feeling touch and controlling body movement.',
  DorsAttn: 'Deliberately directing attention, like choosing where to look.',
  SalVentAttn: 'Noticing what is important or surprising and switching focus to it.',
  Limbic: 'Emotion, smell and reward. Its signal is weak in this kind of scan.',
  Cont: 'Planning, problem-solving and keeping information in mind.',
  Default: 'Active when resting, mind-wandering, remembering or thinking about people.',
}

// Short explanations shown in the "i" tooltips
export const GLOSSARY = {
  connectionStrength:
    'Each connection has a number between -1 and 1 (a correlation, "r"). It measures how closely two ' +
    "regions' activity rose and fell together during the scan: 1 = perfectly in step, 0 = unrelated. " +
    'It is a statistical pattern, not a physical wire.',
  modularity:
    'Modularity measures how cleanly the brain splits into separate groups. It runs from 0 (no ' +
    'grouping) to 1. Above about 0.3 counts as clear grouping. Here the groups are the 7 known networks.',
  headMotion:
    'How much the person moved their head between pictures, on average. Movement blurs the data, so ' +
    'lower is better. Under 0.15 mm counts as low.',
  hub:
    'A hub is a region that many of the shortest routes between other regions pass through, like a busy ' +
    'train interchange. Measured by "betweenness".',
  reproducibility:
    'The same brain was scanned twice, on two different days. This number is how much the two scans ' +
    'agree: the correlation between every connection strength in scan 1 and the same connection in ' +
    'scan 2. Higher means the measurement is stable rather than noise. 1 = identical, 0 = unrelated.',
}

// One-line meaning of the between-scan agreement.
// Input: r between the two scans' connectivity matrices. Output: sentence.
export function describeReproducibility(agreement) {
  if (agreement >= 0.7) return 'The two scans agree strongly, so this connection pattern is a stable feature of this brain.'
  if (agreement >= 0.5) return 'The two scans agree moderately: the broad pattern repeats, but details vary between days.'
  return 'The two scans agree only weakly, so treat individual connections with caution.'
}

// Plain sentence about how stable one region is between the two scans.
// Inputs: stability { strength, rank, rank_change, consistency } for the region (from
//         comparison.json), runLabels ["REST1", "REST2"], regionTotal.
// Output: sentence.
export function describeStability(stability, runLabels, regionTotal) {
  const [first, second] = runLabels
  const moved = Math.abs(stability.rank_change)
  const direction = stability.rank_change > 0 ? 'up' : 'down'
  const movement = moved === 0
    ? `It held the same rank (#${stability.rank[first]} of ${regionTotal}) in both scans`
    : `It moved ${direction} ${moved} place${moved === 1 ? '' : 's'} in the ranking ` +
      `(#${stability.rank[first]} in ${first}, #${stability.rank[second]} in ${second})`
  if (stability.consistency === 'most consistent') {
    return `One of the most consistent regions between scans. ${movement}.`
  }
  if (stability.consistency === 'least consistent') {
    return `One of the least consistent regions between scans. ${movement}.`
  }
  return `About as consistent as most regions between scans. ${movement}.`
}

// Each statistic: an everyday label (with the technical name for researchers) and a
// sentence for high / above-average / typical / low values, plus one for regions with
// no strong links. highShare (optional) changes what counts as "high" (default top 15%).
const STAT_SENTENCES = {
  degree: {
    label: 'Number of strong links (degree)',
    none: 'It has no links strong enough to make the top 10%, so it sits on its own in this network.',
    high: (value) => `It is strongly linked to ${value} other regions, more than most.`,
    above: (value) => `It is strongly linked to ${value} other regions, more than average.`,
    typical: (value) => `It is strongly linked to ${value} other regions, about typical.`,
    low: (value) => `It is strongly linked to only ${value} other regions, fewer than most.`,
  },
  strength: {
    label: 'Total link strength (strength)',
    none: 'With no strong links, its total link strength is zero.',
    high: () => 'Added together, its links are among the strongest in the brain.',
    above: () => 'Added together, its links are stronger than average.',
    typical: () => "Added together, its links are about as strong as a typical region's.",
    low: () => "Added together, its links are weaker than most regions'.",
  },
  betweenness: {
    label: 'Hub score (betweenness)',
    highShare: 0.1, // "hub" is a strong word: keep it for the top 10%
    none: "It doesn't sit on any of the routes between other regions.",
    high: () => 'This region is a hub: it sits on many of the shortest paths between other regions.',
    above: () => 'It often acts as a bridge on the paths between other regions.',
    typical: () => 'It sometimes acts as a bridge on the paths between other regions.',
    low: () => 'It rarely sits on the paths between other regions.',
  },
  clustering: {
    label: 'Tight-knit group (clustering)',
    none: "With no strong links, there's no neighbourhood to measure.",
    high: () => 'Its partners are also closely linked to each other, forming a tight-knit group.',
    above: () => 'Its partners are fairly closely linked to each other.',
    typical: () => 'Its partners are somewhat linked to each other.',
    low: () => 'Its partners are mostly not linked to each other.',
  },
  eigenvector: {
    label: 'Influence (eigenvector)',
    none: "It isn't part of the main connected network, so this is zero.",
    high: () => 'It is linked to other well-connected regions, an influential position.',
    above: () => 'Its partners are fairly well connected themselves.',
    typical: () => 'Its partners are moderately well connected themselves.',
    low: () => 'Its partners are mostly less-connected regions.',
  },
}

// Turn one statistic into a plain sentence.
// Inputs: stat key, the region's value, its rank (1 = highest), total regions,
//         and whether the region has any strong links at all.
// Output: { label, sentence, tier } where tier is "high" | "above" | "typical" | "low" | "none".
export function describeStat(statKey, value, rank, total, hasLinks) {
  const text = STAT_SENTENCES[statKey]
  const highShare = text.highShare ?? 0.15
  let tier = 'typical'
  if (!hasLinks || value === 0) tier = 'none'
  else if (rank <= total * highShare) tier = 'high' // top 15% (10% for hubs)
  else if (rank <= total * 0.4) tier = 'above' // up to the top 40%
  else if (rank > total * 0.7) tier = 'low' // bottom 30%
  const sentence = tier === 'none' ? text.none : text[tier](value)
  return { label: text.label, sentence, tier }
}

// Everyday description of head motion.
// Input: mean relative motion in mm. Output: short phrase.
export function describeMotion(motionMm) {
  if (motionMm < 0.15) return 'very still, so the data are clean'
  if (motionMm < 0.25) return 'some movement, data are usable'
  return 'a lot of movement, so treat results with caution'
}

// One-line meaning of the modularity value.
// Input: modularity (0..1). Output: sentence.
export function describeModularity(modularity) {
  if (modularity >= 0.3) {
    return 'Regions are much more in sync within their own network than with other networks, so the 7 groups are clear.'
  }
  return 'Regions are only a little more in sync within their own network than across networks.'
}
