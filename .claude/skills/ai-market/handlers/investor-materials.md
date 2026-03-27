# Handler: investor-materials

Fundraising collateral: pitch decks, one-pagers, financial models, and accelerator applications. All materials must tell a consistent story backed by the same numbers.

## Golden Rule: All Materials Must Agree

Every investor-facing document draws from a single source of truth. If a number appears in the deck, it must match the one-pager, the financial model, and the application.

### Source of Truth Fields

Maintain these values in one place. Update once, propagate everywhere.

| Field | Example | Where it appears |
|-------|---------|-----------------|
| Traction metrics | "$45K MRR, 120 customers, 15% MoM growth" | Deck slide 4, one-pager section 2, application Q: traction |
| Pricing | "Starter $49/mo, Pro $149/mo, Enterprise custom" | Deck slide 6, financial model revenue assumptions |
| Raise size | "Raising $2M seed on $10M post-money" | Deck slide 11, one-pager header, application Q: raise |
| Use of funds | "60% engineering, 20% GTM, 20% ops" | Deck slide 11, one-pager section 5, financial model expenses |
| Team bios | Name, role, relevant credential (1 line each) | Deck slide 10, one-pager section 4, application Q: team |
| Milestones | "Q3: launch v2, Q4: 500 customers, Q1+1: Series A" | Deck slide 12, financial model projections, application Q: plan |

Before generating any material, ask the user to confirm or provide these values.

## Asset Guidance

### Pitch Deck (12 Slides)

Investors spend an average of 3 minutes and 44 seconds on a deck. Every slide earns its place.

```text
Slide  1: Title (company name, one-line description, logo)
Slide  2: Problem (who has it, how painful, how they cope today)
Slide  3: Solution (what you built, how it solves the problem)
Slide  4: Traction (revenue, users, growth rate -- real numbers)
Slide  5: Market (TAM/SAM/SOM with sources, not fantasy numbers)
Slide  6: Business model (pricing, unit economics, LTV:CAC)
Slide  7: Product (screenshot or demo, not architecture diagram)
Slide  8: How it works (the "why us" -- tech moat, unique insight)
Slide  9: Competition (positioning matrix, not feature checklist)
Slide 10: Team (relevant experience only -- why THIS team wins)
Slide 11: The ask (raise amount, valuation, use of funds breakdown)
Slide 12: Closing (milestones to next round, contact info)
```

Rules:
- One message per slide. If you need two points, you need two slides.
- Numbers over narratives. "15% MoM for 8 months" beats "rapid growth."
- Competition slide: use 2x2 matrix with meaningful axes, not a feature grid where you check every box.
- Product slide shows the product. Not the architecture. Not the tech stack.

### One-Pager / Investment Memo

A single page (PDF or markdown) that an investor forwards to partners.

```text
Structure:
  Header:  Company name | Stage | Raising $X at $Y valuation
  Section 1: Problem & Solution (3-4 sentences)
  Section 2: Traction (key metrics with timeframe)
  Section 3: Market (TAM with source, target segment)
  Section 4: Team (founders with 1-line bios)
  Section 5: Use of Funds (3-4 line items with percentages)
  Section 6: Contact (email, calendly link)
```

Rules:
- Fits on one page when printed. No exceptions.
- Lead with traction if you have it. Lead with team if you are pre-revenue.
- No jargon the investor's partners would need to look up.

### Financial Model

Three-scenario projection (bear, base, bull) with sensitivity analysis.

```text
Structure:
  Tab 1: Assumptions (clearly labeled inputs, color-coded)
  Tab 2: Revenue model (cohort-based or bottoms-up)
  Tab 3: Expense model (headcount plan, COGS, opex)
  Tab 4: P&L summary (monthly for 12mo, quarterly for 24mo)
  Tab 5: Cash flow (burn rate, runway, fundraise timing)
  Tab 6: Sensitivity analysis (what-if on 3-4 key drivers)
```

Scenarios:
- **Bear**: 50% of base case growth, higher churn, slower hiring.
- **Base**: plan-of-record assumptions.
- **Bull**: 150% of base case growth, lower churn, faster expansion.

Sensitivity analysis: vary these drivers independently:
- Monthly growth rate (+/- 5 percentage points).
- Churn rate (+/- 2 percentage points).
- Average contract value (+/- 20%).
- Sales cycle length (+/- 30 days).

Rules:
- Color-code assumptions: blue = input, black = formula, green = linked from another tab.
- Revenue must reconcile: units * price * conversion = revenue. No magic cells.
- Headcount must match use-of-funds slide.
- Include a runway calculation: "At base case burn, runway is X months without additional funding."

### Accelerator Applications

Common questions mapped to source of truth fields.

| Common Question | Source |
|----------------|--------|
| "Describe your company in one sentence" | Deck slide 1 subtitle |
| "What problem do you solve?" | Deck slides 2-3 |
| "What is your traction?" | Traction metrics |
| "How do you make money?" | Pricing + business model |
| "How big is the market?" | Market sizing (TAM/SAM/SOM) |
| "Who is on the team?" | Team bios |
| "How much are you raising?" | Raise size |
| "What will you do with the money?" | Use of funds |
| "What are your milestones for the next 12 months?" | Milestones |
| "Why now?" | Problem slide + market timing argument |

Rules:
- Answer the question asked. Do not dump your pitch into every text box.
- Keep answers concise. If the limit is 200 words, use 150.
- Match tone to the accelerator's brand (YC values directness; others may prefer polish).
- Use the same numbers as the deck. Reviewers cross-reference.

## Red Flags to Avoid

Investors pattern-match on these. Any one can sink a deal.

- **Unverifiable claims**: "We are the only company doing X" (you are probably not). Replace with specific differentiation.
- **Fuzzy market sizing**: "$100B TAM" with no methodology. Always show your math. Top-down AND bottom-up.
- **Inconsistent team roles**: CTO in the deck, "Technical Lead" in the application. Pick one title per person and use it everywhere.
- **Revenue math that does not sum**: if you claim 120 customers at $49/mo, your MRR better be close to $5,880, not "$45K MRR." Investors will check.
- **Vanity metrics without context**: "10,000 sign-ups" means nothing without activation rate, retention, or revenue.
- **Missing competitive response**: "No real competitors" is a red flag. Either you have not looked, or the market does not exist.
- **Vague use of funds**: "product development" is not specific. "Hire 3 engineers to build real-time collaboration (Q2-Q3)" is.
- **Milestone-free plans**: "scale the business" is not a milestone. "Reach $100K MRR by Q4" is.

## Output

- Requested asset(s) in markdown format, ready for design handoff.
- Consistency check: verify all numbers agree across generated materials.
- Red flag audit: flag any claims or numbers that could trigger investor scrutiny.
