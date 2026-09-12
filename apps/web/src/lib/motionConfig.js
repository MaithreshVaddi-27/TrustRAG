// ── Shared Motion Config ─────────────────────────────────────────────────────
// Apple Design: "Think of animation as a conversation between you and the object,
// not something prescribed by the interface."
// Apple Design params (damping ratio 1.0, response 0.3-0.4s) → Motion springs:
// - Critically damped (no overshoot): bounce: 0, duration: 0.35 ≈ damping 22-24, stiffness 280-320
// - Momentum-driven bounce (damping ~0.8): bounce: 0.2, duration: 0.35 ≈ damping 16-18, stiffness 200-220
// Reduced motion: opacity cross-fade only (no springs), per Apple HIG §14

// Critically damped spring — no overshoot, graceful settle
// Used for: layout transitions, sidebar expand/collapse, modal enter
export const SPRING_NORMAL = { type: 'spring', bounce: 0, duration: 0.35 }

// Snappy spring — fast response for micro-interactions (press feedback)
// Used for: button taps, nav link highlights, small element state changes
export const SPRING_SNAPPY = { type: 'spring', bounce: 0, duration: 0.25 }

// Gentle spring — slower, more luxurious feel
// Used for: page entrance, stagger children, hero elements
export const SPRING_GENTLE = { type: 'spring', bounce: 0, duration: 0.5 }

// Bouncy spring — slight overshoot for momentum-driven interactions ONLY
// Used for: drag-release, sheet dismiss, flick gestures — NOT hover
export const SPRING_BOUNCE = { type: 'spring', bounce: 0.2, duration: 0.35 }

// Reduced motion: opacity cross-fade (200ms), no spring — Apple Design §14
// Returned by MotionConfig when prefers-reduced-motion matches
export const REDUCED_MOTION_TRANSITION = { type: 'tween', duration: 0.2, ease: 'easeOut' }

// Default motion config for <MotionConfig> provider
export const DEFAULT_TRANSITION = SPRING_NORMAL
