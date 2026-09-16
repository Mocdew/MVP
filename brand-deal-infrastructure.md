# Deal Desk
### Brand-deal infrastructure for creators

> *Working name — placeholder, swap freely.*

---

## 1. The one-liner

**Creators can't prove what a sponsorship delivered, so they get underpaid for the next one.** Deal Desk connects a creator's YouTube and Instagram, tracks every brand deal against the posts that fulfilled it, and turns that into two things a creator can't get anywhere else: a brand-facing ROI report, and an honest answer to *"what should I be charging?"*

We are not an analytics dashboard. We are the layer where a creator's business is documented, priced, and eventually paid.

---

## 2. The problem, specifically

A creator doing 2–4 paid deals a month lives with three real costs:

1. **No proof.** When the brand asks "how did it perform?", the creator screenshots Instagram Insights into a Google Doc. It takes an hour, it looks amateur, and it doesn't survive comparison to what an agency sends.
2. **No price discovery.** Rates are set by vibes and whisper networks. Creators routinely quote 30–50% under market for their tier because they have no reference point and no leverage.
3. **No paper trail.** Deliverables, dates, usage rights and payment terms live in an email thread. Late payment is chased manually, or not at all.

Native platform analytics solve none of this, because none of it is a metrics problem. It's a business-of-being-a-creator problem.

---

## 3. Product — v1 (six weeks)

One buyer, two connectors, one workflow:

1. **Connect** — OAuth into YouTube and Instagram. Two platforms, both with stable, documented APIs.
2. **Log a deal** — brand, fee, deliverables, dates, usage terms.
3. **Auto-match** — deliverable posts are matched to the deal automatically; performance flows in from the connected accounts.
4. **Report** — a brand-facing ROI report: reach, engagement vs. the creator's own baseline, CPM-equivalent, deliverable completion. Exportable, and shareable as a live link.
5. **Media kit** — the same data rendered as an always-current public page the creator sends to prospects. Never stale, never rebuilt in Canva.

That's the whole v1. A creator can use it end-to-end the week it ships.

---

## 4. What comes next, and why in that order

| Horizon | What ships | Why then |
|---|---|---|
| **Months 2–6** | **Rate index** (benchmark: what creators of your size/vertical/format are actually paid), invoicing + payment chasing, FTC/paid-partnership disclosure checks, agency multi-seat | Each needs deal volume in the system first. The index is worthless at 10 deals and compounding at 10,000. |
| **Months 6–18** | Payments rail with take-rate pricing, brand-side portal, TikTok if and when access allows | Requires trust and volume. Being in the payment path is the endgame for retention and monetization. |
| **Later, conditionally** | Predictive/diagnostic modelling | Only against a proven baseline — see §12. Not a launch claim. |

---

## 5. Business model — decided

| Tier | Price | Who |
|---|---|---|
| **Free** | $0 | Media kit only. Public, shareable, branded. This is distribution, not a product tier. |
| **Pro** | **$49/mo** | Creators doing ≥1 paid deal/month. Unlimited deals, ROI reports, rate index, invoicing. |
| **Agency** | **$39/creator/mo**, 5-seat minimum | Managers running rosters. Roles, permissions, roster-level reporting. |
| **Phase 2** | **1% of deal value** | Once payments run through us. Take rate replaces seat pricing over time. |

**Why $49 holds:** the median target customer runs $3–8K/month in deal value. A single 20% rate correction — the explicit promise of the rate index — returns 10–20× the annual subscription. We are priced against the *upside we create*, not against dashboard tools at $19.

---

## 6. Market size — bottom-up, with assumptions stated

| Step | Figure | Basis |
|---|---|---|
| Professional creators globally (creating as primary or significant income) | ~2,000,000 | Industry estimates; to be validated |
| Share doing recurring paid brand deals | ~15% | Our assumption — the key number to test in diligence |
| **Serviceable creators** | **~300,000** | |
| Subscription TAM @ $49/mo | **~$176M/yr** | |
| Deal volume flowing through that cohort | ~$12B/yr | 300K × ~$40K average annual deal income |
| Payments TAM @ 1% | **~$120M/yr** | |
| **Total** | **~$300M/yr** | |

Honest reading: the subscription business alone does not reach a $100M-ARR outcome. The payments layer is what makes this venture-scale, which is why §4 treats it as the destination rather than a nice-to-have. If the payments thesis fails, this is a capital-efficient $10–20M ARR business — a good company, financed differently.

---

## 7. Competition

| Category | Who | What they do | Why we're not that |
|---|---|---|---|
| Social analytics | Metricool, Later, Sprout, vidIQ, Social Blade, Shield | Descriptive cross-platform dashboards | Deal-unaware. They report on posts; we report on contracts. |
| Brand-side influencer platforms | CreatorIQ, Grin, Aspire, Modash | Campaign management sold to brands | The creator is a line item in someone else's tool. We're the creator's own record. |
| Creator business ops | Passionfroot, Beacons, Pearpop, Lumanu, Karat | Inbound booking, link-in-bio, cashflow advances | Closest neighbours. They handle deal *intake* and *financing*; nobody owns post-deal proof and pricing truth. |

**The gap:** every player touches the deal before it happens. Nobody owns what happened after — which is precisely the data that sets the price of the next one.

---

## 8. Distribution

Creator software lives or dies on acquisition cost. Three motions, in priority order:

1. **The media kit loop.** Free kits are public links a creator sends to brands. The brand opens it, sees the product, and asks their other creators for one. We reach the brand side without buying it.
2. **Agency land-and-expand.** One manager brings 8–30 creators in a single sale. Slower cycle, dramatically better CAC.
3. **Creator affiliate.** Revenue share to creators who teach other creators — the only advertising channel this audience trusts.

Target blended CAC **under $150**. At $49/mo with 60% annual logo retention, LTV lands around $1,000 gross-margin-adjusted — payback under four months.

---

## 9. Moat

The rate index. Every logged deal — fee, deliverables, delivered performance — makes it more accurate, and it cannot be assembled by scraping, bought, or replicated by an incumbent without our transaction volume.

It is the only asset here that compounds. Everything else in the product is a well-executed workflow.

Data rights for anonymized, aggregated benchmarking are in the terms of service from day one, with an opt-out. Retrofitting that later is legally and reputationally expensive.

---

## 10. Cost structure

- **Platform APIs:** YouTube Analytics and Instagram Graph are free at our volume. No $5K/mo data bills — that is a direct consequence of the platforms we chose *not* to support.
- **Infrastructure:** ingestion, storage and report rendering run at roughly $1–2 per creator per month.
- **No LLM inference in v1.** The natural-language assistant is deliberately out of scope, because unbounded inference cost against a fixed subscription is a margin trap.

Gross margin at v1: **>85%**.

---

## 11. Risks, stated plainly

| Risk | Our position |
|---|---|
| **Platform API dependency** | Real, and the reason we ship only YouTube and Instagram — the two with stable third-party access. TikTok has no viable third-party analytics API today; we plan as if it never arrives. X is excluded on cost and irrelevance to brand deals. |
| **Instagram app review** | Gating risk on launch. Mitigation: YouTube-only mode is fully functional, so review delay slows us rather than blocks us. |
| **Brands reject third-party reports** | Must be validated pre-build. The design partner test is a real brand accepting a real report — see §14. |
| **Passionfroot/Beacons expand into reporting** | Likely within 18 months. Our defense is the rate index, which needs volume they'd have to start accumulating from zero. Speed matters. |
| **Creator churn is career churn** | Structural to the category. Mitigated by moving up-market (creators with existing deal flow, not aspirants) and by entering the payment path. |

---

## 12. How we'll treat models when they return

We are not shipping predictive features at launch, and the reason is a standard we intend to hold ourselves to later:

- Every model states its **baseline** — for content performance, that's the creator's own trailing median for that format.
- Backtested on **held-out creators**, not held-out posts.
- Ships only at **>15% lift** over baseline.
- Outputs carry **intervals**, and are **suppressed below a data threshold**. "Not enough history yet" is a better product than a confident wrong number.

A dashboard that is visibly wrong in week two is unrecoverable. We would rather ship less and be believed.

---

## 13. Compliance and trust

- **GDPR/CCPA:** audience demographic data is aggregate-only; per-creator data export and deletion from day one.
- **Platform ToS:** official APIs only, no scraping. This constrains the product and is a deliberate choice.
- **Multi-tenancy:** role-based access for agency rosters; strict per-creator isolation, audited before the first agency contract.
- **Cold start:** Instagram backfills roughly two years, YouTube substantially more. First-run experience is built around the *first deal logged*, not around a historical dashboard — the product is useful on day one with zero history, which is exactly why the deal is the primitive and not the post.

---

## 14. What we'll prove before raising

1. Written confirmation of data access and cost for every platform we claim.
2. 15 creator/manager interviews with a stated dollar willingness-to-pay.
3. 3 signed design partners with scoped letters.
4. **One real creator sending one generated ROI report to one real brand — and the brand's reply.**

Item 4 is worth more than the other three combined.

**Company metrics from day one:** activation (first deal logged within 7 days), reports sent to brands, deals tracked per creator per month, deal value under management, net revenue retention.

---

## 15. What we are deliberately not building

Stated because knowing what to cut is the thesis:

- **Virality prediction** — insufficient per-creator data, cannot reliably beat a trailing-median baseline.
- **Best-time-to-post** — free in three competing products. Not chargeable.
- **Follower growth forecasting** — creator growth is jump-driven; forecasts are visibly wrong and destroy trust.
- **Cross-platform audience overlap** — not computable without identity resolution we don't have. We won't claim it.
- **Content decay detection** — a dashboard line later, not a module now.
- **AI assistant** — a natural-language layer over a dataset that doesn't exist yet. It becomes obvious once deal history does.
- **TikTok, X, Twitch** — excluded on data access, cost, and relevance, respectively.
- **Alerting** — nobody buys software for notifications.

Each is reversible from a position of having customers. None is worth delaying that position.

---

## 16. Summary

| | |
|---|---|
| **Who** | Creators doing ≥1 paid brand deal per month, and the managers who run their rosters |
| **What** | Deal tracking → brand-facing ROI proof → market-rate benchmarking → payments |
| **Why us, why now** | Deal volume is the only proprietary dataset in the creator economy nobody has assembled, and the tools adjacent to it are all pointed at intake rather than outcome |
| **v1** | Two connectors, one workflow, six weeks |
| **Moat** | The rate index, compounding per transaction |

---

### Assumptions flagged for validation

- 15% of professional creators do recurring paid deals (§6) — the single most load-bearing number in this document.
- Brands will accept a creator-generated third-party report as proof of performance (§11).
- $49/mo clears for creators at $3–8K monthly deal volume (§5).
- Blended CAC under $150 is achievable via the media-kit loop (§8).
