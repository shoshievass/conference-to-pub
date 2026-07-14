# Conference summary statistics

Generated from `data/papers_enriched.json`. A paper presented at multiple conferences is one appearance at each conference.

## Coverage and status

| Conference | Appearances | Published | R&R | Working paper |
|---|---:|---:|---:|---:|
| Cowles Structural Micro / M&M | 111 | 49 | 17 | 45 |
| FTC Micro | 177 | 127 | 11 | 39 |
| NBER IO Spring | 124 | 81 | 19 | 24 |
| NBER SI IO | 132 | 74 | 23 | 35 |
| Northwestern Antitrust | 113 | 73 | 8 | 32 |
| Utah WBEC | 117 | 82 | 12 | 23 |
| **All** | **774** | **486** | **90** | **198** |

## Top-five journal outcomes

Numerator: appearances published or under R&R at AER, JPE, QJE, REStud, or Econometrica. Denominator: all appearances at that conference.

| Conference | Top-five published or R&R | All appearances | Share |
|---|---:|---:|---:|
| Cowles Structural Micro / M&M | 49 | 111 | 44.1% |
| FTC Micro | 55 | 177 | 31.1% |
| NBER IO Spring | 75 | 124 | 60.5% |
| NBER SI IO | 69 | 132 | 52.3% |
| Northwestern Antitrust | 36 | 113 | 31.9% |
| Utah WBEC | 61 | 117 | 52.1% |

## Conference-to-publication time

Journal issue year minus presentation year, for published appearances with an issue year. Negative values mean a conference presented an already-published paper.

| Conference | N | Median | Mean | IQR | Range |
|---|---:|---:|---:|---:|---:|
| Cowles Structural Micro / M&M | 45 | 3 | 3.58 | 2–5 | 1–8 |
| FTC Micro | 122 | 3 | 3.49 | 2–4 | -1–16 |
| NBER IO Spring | 71 | 3 | 3.44 | 2–4 | 1–12 |
| NBER SI IO | 61 | 3 | 3.23 | 2–4 | 1–7 |
| Northwestern Antitrust | 70 | 2 | 2.91 | 1–4 | 0–13 |
| Utah WBEC | 79 | 3 | 3.08 | 2–4 | 0–7 |

## Same-year overlap

An appearance is overlapping when the same canonical paper appears at more than one conference in that calendar year.

| Year | Overlapping appearances | All appearances | Share |
|---:|---:|---:|---:|
| 2008 | 0 | 16 | 0.0% |
| 2009 | 0 | 12 | 0.0% |
| 2010 | 2 | 18 | 11.1% |
| 2011 | 2 | 27 | 7.4% |
| 2012 | 2 | 32 | 6.2% |
| 2013 | 4 | 32 | 12.5% |
| 2014 | 6 | 33 | 18.2% |
| 2015 | 8 | 42 | 19.0% |
| 2016 | 4 | 53 | 7.5% |
| 2017 | 6 | 52 | 11.5% |
| 2018 | 12 | 60 | 20.0% |
| 2019 | 7 | 52 | 13.5% |
| 2020 | 2 | 38 | 5.3% |
| 2021 | 2 | 46 | 4.3% |
| 2022 | 8 | 58 | 13.8% |
| 2023 | 6 | 58 | 10.3% |
| 2024 | 8 | 53 | 15.1% |
| 2025 | 7 | 45 | 15.6% |
| 2026 | 6 | 47 | 12.8% |

## Cross-conference recurrence

There are **78** canonical papers appearing at two or more conferences. Of these, **49** distinct paper/direction transitions occur in a later year.

| Earlier conference | Later conference | Papers |
|---|---|---:|
| FTC Micro | NBER IO Spring | 11 |
| Cowles Structural Micro / M&M | NBER IO Spring | 6 |
| FTC Micro | Northwestern Antitrust | 4 |
| Northwestern Antitrust | NBER IO Spring | 4 |
| Northwestern Antitrust | Utah WBEC | 4 |
| Cowles Structural Micro / M&M | NBER SI IO | 3 |
| FTC Micro | Utah WBEC | 3 |
| Northwestern Antitrust | FTC Micro | 3 |
| FTC Micro | NBER SI IO | 2 |
| NBER SI IO | FTC Micro | 2 |
| Cowles Structural Micro / M&M | FTC Micro | 1 |
| NBER IO Spring | Cowles Structural Micro / M&M | 1 |
| Northwestern Antitrust | NBER SI IO | 1 |
| Utah WBEC | Cowles Structural Micro / M&M | 1 |
| Utah WBEC | NBER IO Spring | 1 |
| Utah WBEC | NBER SI IO | 1 |
| Utah WBEC | Northwestern Antitrust | 1 |

For recurring papers with one unambiguous first conference and a later appearance elsewhere:

| First conference | Papers |
|---|---:|
| FTC Micro | 16 |
| Cowles Structural Micro / M&M | 8 |
| Northwestern Antitrust | 8 |
| Utah WBEC | 3 |
| NBER IO Spring | 1 |
| NBER SI IO | 1 |

## Matching method

Canonical-paper clusters are the transitive closure of exact normalized agenda titles, exact normalized published titles, and exact DOI/AEA article identifiers. This follows title changes without merging records merely because they share an author-page URL.
