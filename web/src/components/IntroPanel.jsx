import { useEffect, useRef } from 'react'
import { SECONDS_PER_TIMEPOINT } from '../utils/explanations.js'

// Welcome card explaining what the picture shows, in plain language.
// Inputs: runInfo (the scan on screen, from subject.json), networkColors, onClose().
// Output: a dialog over the 3D view.
export default function IntroPanel({ runInfo, networkColors, onClose }) {
  const startButtonRef = useRef(null)
  const scanMinutes = Math.round((runInfo.timepoints * SECONDS_PER_TIMEPOINT) / 60)
  const sampleColors = Object.values(networkColors)

  // Put keyboard focus on the main button, and let Esc close the card
  useEffect(() => {
    startButtonRef.current?.focus()
    function handleKey(event) {
      if (event.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', handleKey)
    return () => window.removeEventListener('keydown', handleKey)
  }, [onClose])

  return (
    <div
      className="intro-backdrop"
      onClick={onClose}
      // Reading or closing the card shouldn't count as the interaction that stops auto-rotate
      onPointerDown={(event) => event.stopPropagation()}
    >
      <div
        className="intro-card"
        role="dialog"
        aria-modal="true"
        aria-labelledby="intro-title"
        onClick={(event) => event.stopPropagation()}
      >
        <h2 id="intro-title">What you're looking at</h2>
        <p className="intro-lead">
          This is one real person's brain, scanned by the{' '}
          <strong>Human Connectome Project</strong> while they lay still and rested for about{' '}
          {scanMinutes} minutes. They were scanned twice, on two different days. Switch between the two scans
          with the <strong>REST1 / REST2</strong> buttons to see how well they agree.
        </p>

        <ul className="intro-list">
          <li>
            <span className="intro-icon">
              <span className="intro-ball" style={{ background: sampleColors[2] }} />
            </span>
            <span>
              <strong>Each ball is a brain region.</strong> The brain's outer layer is divided into 200 regions.
            </span>
          </li>
          <li>
            <span className="intro-icon">
              <span className="intro-line"
                style={{ background: `linear-gradient(90deg, ${sampleColors[1]}, ${sampleColors[6]})` }} />
            </span>
            <span>
              <strong>A line means two regions tend to be active at the same time</strong> during rest. Thicker,
              brighter lines mean more closely in sync.
            </span>
          </li>
          <li>
            <span className="intro-icon intro-swatches">
              {sampleColors.slice(0, 4).map((color) => (
                <span key={color} style={{ background: color }} />
              ))}
            </span>
            <span>
              <strong>Colors group regions into 7 known networks</strong> that tend to work together, such as
              vision or movement.
            </span>
          </li>
        </ul>

        <p className="intro-callout">
          <strong>The lines are not physical wires.</strong> They are statistical correlations: they show which
          regions rise and fall together in activity, not the actual nerve fibres connecting them.
        </p>

        <p className="muted small">
          Drag to turn the brain, scroll to zoom, and click any ball or spot on the surface to learn about that
          region. Reopen this guide any time with the <strong>?</strong> button.
        </p>

        <button ref={startButtonRef} type="button" className="primary-button" onClick={onClose}>
          Start exploring
        </button>
      </div>
    </div>
  )
}
