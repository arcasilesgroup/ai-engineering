# Stagger & Debugging

## Stagger Animations

When multiple elements enter together, stagger 30-80ms between items. Long delays make the interface feel slow. Decorative — never block interaction.

```css
.item { opacity: 0; transform: translateY(8px); animation: fadeIn 300ms ease-out forwards; }
.item:nth-child(1) { animation-delay: 0ms; }
.item:nth-child(2) { animation-delay: 50ms; }
.item:nth-child(3) { animation-delay: 100ms; }
@keyframes fadeIn { to { opacity: 1; transform: translateY(0); } }
```

## Debugging

- **Slow motion**: temporarily 2-5x duration, watch for color overlap, abrupt easing, wrong transform-origin, out-of-sync properties.
- **Frame-by-frame**: Chrome DevTools Animations panel for timing between coordinated properties.
- **Real devices**: gesture testing requires physical hardware (USB + Safari remote devtools); simulators miss touch latency.
