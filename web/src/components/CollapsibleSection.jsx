// A sidebar section whose heading can be clicked to fold it away.
// Uses the browser's built-in <details> element, so it works with the keyboard
// and screen readers without extra code.
// Inputs: title, defaultOpen (true), actions (optional controls shown beside the
//         title, e.g. "show all"), children (the section's content).
// Output: a <details> element.
export default function CollapsibleSection({ title, defaultOpen = true, actions, children }) {
  return (
    <details className="section" open={defaultOpen}>
      <summary className="section-summary">
        <span className="section-chevron" aria-hidden="true" />
        <span className="section-title">{title}</span>
        {actions && (
          // Clicking these controls shouldn't also fold the section
          <span className="section-actions" onClick={(event) => event.preventDefault()}>
            {actions}
          </span>
        )}
      </summary>
      <div className="section-body">{children}</div>
    </details>
  )
}
