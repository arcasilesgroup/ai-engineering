# Handler: market-research

Research synthesis that moves from raw information to defensible decisions. Structured for investors, operators, and strategists.

## Modes

Select the mode that matches the research question. If unclear, ask the user.

### 1. Investor/Fund Diligence

Evaluate a company, fund, or opportunity for investment decision-making.

**Scope**:
- Business model viability and unit economics.
- Market position and competitive dynamics.
- Team assessment (founder-market fit, key person risk).
- Financial health (burn rate, runway, revenue trajectory).
- Risk factors (regulatory, technical, market timing).

**Key questions to answer**:
- What is the company's unfair advantage?
- Is the business model sustainable at scale?
- What are the top 3 risks to the investment thesis?
- What would need to be true for this to return 10x?

### 2. Competitive Analysis

Map the competitive landscape for strategic positioning.

**Scope**:
- Direct and indirect competitors (identify 5-10).
- Feature comparison matrix across key dimensions.
- Pricing and packaging comparison.
- Go-to-market strategy differences.
- Strengths, weaknesses, and gaps for each player.

**Key questions to answer**:
- Where is the white space in the market?
- What do customers complain about with existing solutions?
- Which competitor is best positioned and why?
- What would a new entrant need to win?

### 3. Market Sizing

Estimate addressable market using both top-down and bottom-up methods.

**Top-down (TAM/SAM/SOM)**:
```text
TAM (Total Addressable Market)
  = Total market revenue if 100% adoption
  Source: industry reports, analyst estimates

SAM (Serviceable Addressable Market)
  = TAM filtered by geography, segment, and product fit
  Source: TAM * segment percentage

SOM (Serviceable Obtainable Market)
  = SAM filtered by realistic capture rate
  Source: SAM * estimated market share (typically 1-5% for entrants)
```

**Bottom-up**:
```text
SOM = (target customers) * (annual contract value) * (conversion rate)

Example:
  50,000 target companies in segment
  * $12,000 ACV
  * 2% conversion in year 1
  = $12M year-1 revenue
```

Rules:
- Always present both methods. If they diverge by >3x, explain why.
- State assumptions explicitly. Every number must trace to a source or assumption.
- Use conservative estimates for SOM. Aggressive projections erode credibility.

### 4. Technology/Vendor Research

Evaluate technology choices or vendor selection for build-vs-buy decisions.

**Scope**:
- Requirements mapping (must-have, nice-to-have, out-of-scope).
- Vendor comparison across: capability, pricing, support, lock-in risk.
- Total cost of ownership over 3-year horizon (license, integration, migration, support).
- Community and ecosystem health (GitHub stars are vanity; contributor count and release cadence matter).

**Key questions to answer**:
- What is the switching cost if this vendor fails or pivots?
- Does this technology solve the problem or just shift it?
- What is the team's ramp-up time?
- What do teams who left this technology migrate to, and why?

## Output Format

Every research deliverable follows this structure:

```text
1. Executive Summary (3-5 sentences, the decision in plain language)
2. Key Findings (5-7 bullet points, each with supporting evidence)
3. Implications (what this means for the decision at hand)
4. Risks and Caveats (what could invalidate these findings)
5. Recommendation (clear position with confidence level: high/medium/low)
6. Sources (numbered list, every claim traced to a source)
```

## Standards

- **Every claim sourced**. No unsourced assertions. If a data point comes from an assumption, label it as such.
- **Data older than 18 months flagged**. Prefix with "[DATA: YYYY]" so the reader knows the vintage.
- **Contrarian evidence included**. For every key finding, include at least one data point or argument that challenges it. Label as "Counter-evidence" or "Alternative view."
- **Confidence levels stated**. Rate each key finding as high/medium/low confidence based on source quality and corroboration.
- **No weasel words**. Replace "some analysts believe" with "Gartner's 2025 report estimates" or "based on 3 customer interviews." If the source is weak, say so directly.
- **Separate facts from interpretation**. Present data first, then state what you conclude from it. Do not blend them.

## Anti-patterns

- Market sizing with only top-down estimates and no bottom-up validation.
- Competitive analysis that only lists features without analyzing strategic implications.
- Diligence reports that omit risk factors or present only the bull case.
- Vendor research that compares marketing claims instead of documented capabilities.
- Using a single source for a critical claim.

## Output

- Structured research document in the output format above.
- All sources numbered and traceable.
- Confidence level stated for the overall recommendation.
