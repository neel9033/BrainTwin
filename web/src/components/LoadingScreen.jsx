// Full-screen loading state shown while the brain files download and the 3D scene
// draws its first frame. Fades out once everything is ready.
// Inputs: progress { fraction 0..1, label }, isDone (true = fade out), subjectId.
// Output: an overlay element.
export default function LoadingScreen({ progress, isDone, subjectId }) {
  const percent = Math.round((progress?.fraction ?? 0) * 100)
  return (
    <div className={`loading-screen ${isDone ? 'is-done' : ''}`} aria-hidden={isDone}>
      <div className="loading-card" role="status" aria-live="polite">
        <div className="loading-pulse" aria-hidden="true">
          <span />
          <span />
          <span />
        </div>
        <p className="loading-title">Loading {subjectId}</p>
        <div
          className="loading-bar"
          role="progressbar"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={percent}
          aria-label="Loading progress"
        >
          <span style={{ width: `${percent}%` }} />
        </div>
        <p className="loading-label">
          {percent < 100 ? progress?.label ?? 'Starting' : 'Preparing the 3D view'}
          <span className="loading-percent">{percent}%</span>
        </p>
      </div>
    </div>
  )
}
