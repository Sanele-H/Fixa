"""Fair ranking, trust summary, price range and the fairness simulation for Fixa (P4).

Owner: P4. Only P4 edits files in packages/ranking/. P2's API imports this package.

Public functions (the contract; signatures change only with the team's agreement):
    rank_providers(job, candidates, rng) -> list[RankedProvider]
    trust_summary(stats) -> TrustSummary(score, low, high, n_evidence, breakdown, label)
    price_range(trade, size, area, accepted_quotes) -> PriceRange | None

All randomness takes a seeded rng. The fairness simulation reuses rank_providers unchanged.
P4 also generates the demo data in data/seed/.

Step 0 (Day 1): stubs with the correct return types, so the API can import them.
"""
