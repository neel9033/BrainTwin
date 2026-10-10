import { VIEW_DIRECTIONS } from './CameraRig.jsx'

// Row of preset camera buttons plus an auto-rotate switch, floating over the 3D view.
// Inputs: onView(name), autoRotate (bool), onToggleAutoRotate().
// Output: a <nav> element.
export default function ViewBar({ onView, autoRotate, onToggleAutoRotate }) {
  return (
    <nav className="view-bar" aria-label="Camera views">
      {Object.keys(VIEW_DIRECTIONS).map((name) => (
        <button key={name} type="button" onClick={() => onView(name)}>
          {name}
        </button>
      ))}
      <span className="view-bar-divider" />
      <button
        type="button"
        className={autoRotate ? 'is-on' : ''}
        aria-pressed={autoRotate}
        // Keep this press from counting as the "interaction" that switches auto-rotate off
        onPointerDown={(event) => event.stopPropagation()}
        onClick={onToggleAutoRotate}
      >
        Auto-rotate
      </button>
    </nav>
  )
}
