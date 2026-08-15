# Motion

Loads only when the diff carries real movement, a gesture or a transition. "Make it prettier"
is not motion, and a static layout defect is not judged here.

- Purpose first: what does this movement tell the person that stillness would not? Motion
  with no answer is decoration, and decoration on every interaction is noise.
- Duration and curve: a transition long enough to be noticed twice is too long. Say the
  number and the easing, not "feels smooth".
- Interruptible: a person who changes their mind mid-animation gets the new state, not a
  queue. An animation that must finish is a control that stops responding.
- `prefers-reduced-motion` has a real alternative, not a disabled feature — the state change
  still happens, without the travel.
- Gestures: the threshold, what happens on release below it, and what a keyboard does
  instead of the gesture.
- Performance budget: what is animated (transform and opacity, or something that lays out
  again), on what hardware, and the frame cost measured rather than assumed.
- This lens judges fidelity to the spec. It does not redesign the motion and does not repair
  it; a finding goes back to the diff's author with the number that failed.
