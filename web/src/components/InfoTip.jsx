import { useId, useRef, useState } from 'react'
import { createPortal } from 'react-dom'

const TOOLTIP_WIDTH = 260

// A small "i" button that shows an explanation on hover, keyboard focus, or tap.
// The tooltip is drawn at the top level of the page so panels with scrolling
// don't cut it off.
// Inputs: text (the explanation), label (what it explains, for screen readers).
// Output: a button, plus the tooltip while open.
export default function InfoTip({ text, label }) {
  const buttonRef = useRef(null)
  const tooltipId = useId()
  const [position, setPosition] = useState(null) // { left, top } while open

  // Place the tooltip under the button, kept inside the window
  function open() {
    const box = buttonRef.current.getBoundingClientRect()
    const left = Math.min(Math.max(8, box.left + box.width / 2 - TOOLTIP_WIDTH / 2),
      window.innerWidth - TOOLTIP_WIDTH - 8)
    setPosition({ left, top: box.bottom + 6 })
  }
  function close() {
    setPosition(null)
  }

  return (
    <>
      <button
        ref={buttonRef}
        type="button"
        className="info-tip"
        aria-label={`What is ${label}?`}
        aria-describedby={position ? tooltipId : undefined}
        onMouseEnter={open}
        onMouseLeave={close}
        onFocus={open}
        onBlur={close}
        onClick={(event) => {
          event.preventDefault() // don't toggle a surrounding checkbox label
          if (position) close()
          else open()
        }}
      >
        i
      </button>
      {position &&
        createPortal(
          <div id={tooltipId} role="tooltip" className="info-tooltip"
            style={{ left: position.left, top: position.top, width: TOOLTIP_WIDTH }}>
            {text}
          </div>,
          document.body,
        )}
    </>
  )
}
