// GENERATED FILE — do not edit. Source: brand/tokens.json. Regenerate: bun scripts/brand.ts gen
//
// The terminal owns its own background, so the CLI never paints prose in the brand
// green: the banner frame and braces carry the brand, the wordmark is left at the
// terminal's default foreground (legible on a light terminal and a dark one alike),
// and the status marks use the terminal's own named ANSI colours, which every theme
// already tunes for legibility. Under NO_COLOR or a piped stdout, styleText returns
// the text untouched and the CLI emits no escape bytes at all.

/** The one brand colour in the terminal: the banner frame and its braces. */
export const BANNER_GREEN = '#00ED64';

/** The dim version line under the logo. */
export const BANNER_META = 'dim';

/** Status marks, by terminal-native colour name. */
export const MARKS = {
  ok: 'green',
  info: 'blue',
  head: 'blue',
  warn: 'yellow',
  fail: 'red',
  muted: 'dim',
} as const;
