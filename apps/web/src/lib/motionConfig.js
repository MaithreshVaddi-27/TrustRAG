// ── Shared Motion Config ─────────────────────────────────────────────────────
// Apple Design: "Think of animation as a conversation between you and the object,
// not something prescribed by the interface."
// Apple Design params (damping ratio 1.0, response 0.3-0.4s) → Motion springs:
// - Critically damped (no overshoot): bounce: 0, duration: 0.35 ≈ damping 22-24, stiffness 280-320
// - Momentum-driven bounce (damping ~0.8): bounce: 0.2, duration: 0.35 ≈ damping 16-18, stiffness 200-220
// Reduced motion: opacity cross-fade only (no springs), per Apple HIG §14

// Snappy spring — fast response for micro-interactions (press feedback)
// Used for: button taps, nav link highlights, small element state changes
export const SPRING_SNAPPY = { type: 'spring', bounce: 0, duration: 0.25 }

// Gentle spring — slower, more luxurious feel
// Used for: page entrance, stagger children, hero elements
export const SPRING_GENTLE = { type: 'spring', bounce: 0, duration: 0.5 }
