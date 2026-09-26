/** Pure lines for a doctor check: Zed cannot enforce the gate; denying carriers that still run the chain stay named. */

export type CheckpointGateSurface = {
  readonly id: string;
  readonly label?: string;
  readonly carriers: readonly unknown[];
  readonly can: { readonly deny: boolean | "throw" | "host-only" };
};

function runsAiEngChain(text: string): boolean {
  return /ai-eng chain/.test(text);
}

function isDenying(deny: CheckpointGateSurface["can"]["deny"]): boolean {
  return deny === true || deny === "throw";
}

/**
 * Lines a doctor check can print.
 * - Zed (host-only deny, no carrier): checkpoint gate unenforced.
 * - A denying surface whose carrier text still runs `ai-eng chain`: chain active.
 */
export function checkpointGateReportLines(
  surfaces: readonly CheckpointGateSurface[],
  carrierTemplates: Readonly<Record<string, string>>,
): string[] {
  const lines: string[] = [];

  for (const surface of surfaces) {
    if (surface.id === "zed" || surface.can.deny === "host-only") {
      if (surface.carriers.length === 0) {
        const name = surface.label ?? surface.id;
        lines.push(`${name}: checkpoint gate unenforced (no carrier, deny is host-only)`);
      }
    }
  }

  for (const surface of surfaces) {
    if (!isDenying(surface.can.deny)) continue;
    const text = carrierTemplates[surface.id];
    if (text === undefined || !runsAiEngChain(text)) continue;
    lines.push(`${surface.id}: chain active`);
  }

  return lines;
}
