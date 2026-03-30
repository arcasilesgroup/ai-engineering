# Handler: Gesture and Drag Interactions

## Purpose
Rules for building gesture-based interactions: swipe, drag, pinch, and dismissal patterns.

## Momentum-based dismissal

Don't require dragging past threshold. Calculate velocity: `Math.abs(dragDistance) / elapsedTime`. If velocity exceeds ~0.11, dismiss regardless of distance. A quick flick should be enough.

```js
const timeTaken = new Date().getTime() - dragStartTime.current.getTime();
const velocity = Math.abs(swipeAmount) / timeTaken;

if (Math.abs(swipeAmount) >= SWIPE_THRESHOLD || velocity > 0.11) {
  dismiss();
}
```

## Damping at boundaries

When a user drags past natural boundary (e.g., dragging drawer up when already at top), apply damping. The more they drag, the less element moves. Things in real life don't suddenly stop; they slow down first.

## Pointer capture for drag

Once dragging starts, set element to capture all pointer events. This ensures dragging continues even if pointer leaves element bounds.

## Multi-touch protection

Ignore additional touch points after initial drag begins. Without this, switching fingers mid-drag causes element to jump to new position.

```js
function onPress() {
  if (isDragging) return;
  // Start drag...
}
```

## Friction instead of hard stops

Instead of preventing upward drag entirely, allow it with increasing friction. It feels more natural than hitting an invisible wall.
