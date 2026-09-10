// ── Shared Motion Config ─────────────────────────────────────────────────────
// Apple Design: "Think of animation as a conversation between you and the object,
// not something prescribed by the interface."

// Critically damped spring — no overshoot, graceful settle
// Used for: layout transitions, sidebar expand/collapse, modal enter
export const SPRING_NORMAL = { type: 'spring', damping: 22, stiffness: 280 }

// Snappy spring — fast response for micro-interactions
// Used for: button taps, nav link highlights, small element state changes
export const SPRING_SNAPPY = { type: 'spring', damping: 24, stiffness: 320 }

// Gentle spring — slower, more luxurious feel
// Used for: page entrance, stagger children, hero elements
export const SPRING_GENTLE = { type: 'spring', damping: 20, stiffness: 180 }

// Bouncy spring — slight overshoot for momentum interactions
// Used for: card hover lift, playful micro-interactions
export const SPRING_BOUNCE = { type: 'spring', damping: 16, stiffness: 220 }

// Critically damped for accessibility
export const SPRING_REDUCED = { type: 'spring', damping: 100, stiffness: 400 }

// Default motion config for <MotionConfig> provider
export const DEFAULT_TRANSITION = SPRING_NORMAL
