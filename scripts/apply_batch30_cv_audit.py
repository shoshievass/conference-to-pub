#!/usr/bin/env python3
"""Apply the July 2026 author-CV/research-page audit to lookup batch 30.

This file is intentionally explicit: conference titles often changed before
publication, so each promotion below is a reviewed same-project match rather
than a fuzzy-title match.  Accepted and forthcoming papers use the project's
``published`` status; R&Rs require a named journal.
"""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOOKUP = ROOT / "data" / "lookups" / "batch-30.json"


def published(journal, year, title, url, note):
    return {
        "status": "published",
        "journal": journal,
        "pub_year": year,
        "published_title": title,
        "url": url,
        "note": note,
    }


def rr(journal, url, note):
    return {
        "status": "rr",
        "journal": journal,
        "pub_year": None,
        "published_title": None,
        "url": url,
        "note": note,
    }


OVERRIDES = {
    "ftc2008-08": published("AEJ: Microeconomics", 2010, "Why Tie a Product Consumers Do Not Use?", "https://doi.org/10.1257/mic.2.3.85", "Michael Waldman's CV identifies the conference project as the 2010 AEJ: Microeconomics article; the published title drops the explanatory subtitle. CV/publication match rechecked Jul 2026."),
    "ftc2008-11": published("Review of Economics and Statistics", 2013, "Evidence on the Accuracy of Merger Simulations", "https://doi.org/10.1162/REST_a_00347", "Same Matthew Weinberg merger-simulation project, published under a revised title. Author/publication record rechecked Jul 2026."),
    "ftc2008-12": published("Econometrica", 2012, "Improving the Numerical Performance of Static and Dynamic Aggregate Discrete Choice Random Coefficients Demand Estimation", "https://doi.org/10.3982/ECTA8585", "Jeremy Fox's CV identifies the Econometrica article as the later version of the conference paper. Rechecked Jul 2026."),
    "ftc2008-15": published("Marketing Science", 2010, "Analyzing the Relationship Between Organic and Sponsored Search Advertising: Positive, Negative, or Zero Interdependence?", "https://doi.org/10.1287/mksc.1090.0552", "Same Ghose-Yang search-advertising project, published under a revised title. Author/publication record rechecked Jul 2026."),
    "ftc2009-03": published("Review of Economics and Statistics", 2016, "The Relationship between Market Structure and Innovation in Industry Equilibrium: A Case Study of the Global Automobile Industry", "https://doi.org/10.1162/REST_a_00494", "Same automobile-industry project and authors, published under an expanded title. Author/publication record rechecked Jul 2026."),
    "ftc2009-06": published("International Journal of Industrial Organization", 2013, "Can Information Costs Affect Consumer Choice? Nutritional Labels in a Supermarket Experiment", "https://doi.org/10.1016/j.ijindorg.2010.11.002", "The FTC draft and published Kiesel-Villas-Boas article use the same supermarket shelf-label experiment, authors, and design; the title changed before publication. Rechecked Jul 2026."),
    "ftc2009-08": published("American Economic Review", 2013, "Ownership Consolidation and Product Characteristics: A Study of the US Daily Newspaper Market", "https://doi.org/10.1257/aer.103.5.1598", "Same Ying Fan newspaper-market project, published under a revised title. Author/publication record rechecked Jul 2026."),
    "ftc2010-02": published("International Journal of Industrial Organization", 2011, "Do Physician Incentives Affect Hospital Choice? A Progress Report", "https://doi.org/10.1016/j.ijindorg.2010.11.003", "Kate Ho's research page and CV list the IJIO article arising from this physician-incentives project. Rechecked Jul 2026."),
    "ftc2010-04": published("Review of Economic Studies", 2015, "Consumer Inattention and Bill-Shock Regulation", "https://doi.org/10.1093/restud/rdu024", "Michael Grubb's CV connects the preliminary penalty-pricing/bill-shock project to the Review of Economic Studies article. Rechecked Jul 2026."),
    "ftc2010-07": published("RAND Journal of Economics", 2011, "Targeting in Advertising Markets: Implications for Offline versus Online Media", "https://doi.org/10.1111/j.1756-2171.2011.00143.x", "Same Bergemann-Bonatti advertising-targeting project, published with a modestly revised title. Rechecked Jul 2026."),
    "ftc2011-01": published("Real Estate Economics", 2018, None, "https://doi.org/10.1111/1540-6229.12234", "Exact-title author and journal match. Publication record rechecked Jul 2026."),
    "ftc2011-06": published("B.E. Journal of Theoretical Economics", 2014, "Adverse Effects of Patent Pooling on Product Development and Commercialization", "https://doi.org/10.1515/bejte-2013-0038", "Same Jeitschko-Zhang patent-pool product-development project, published under a revised title. Rechecked Jul 2026."),
    "ftc2011-07": published("American Economic Review", 2015, "Cellular Service Demand: Biased Beliefs, Learning, and Bill Shock", "https://doi.org/10.1257/aer.20120283", "Same Matthew Osborne cellular-service demand project, published under a shortened title. Rechecked Jul 2026."),
    "ftc2012-04": published("Quantitative Marketing and Economics", 2015, "Display Advertising's Competitive Spillovers to Consumer Search", "https://doi.org/10.1007/s11129-015-9155-0", "Same Randall Lewis display-advertising/search project, published under a revised title. Rechecked Jul 2026."),
    "ftc2012-05": published("Management Science", 2020, "A Structural Model of Correlated Learning and Late-Mover Advantages: The Case of Statins", "https://doi.org/10.1287/mnsc.2018.3221", "Same Ching-Ishihara statins/detailing project, published under a revised title. Rechecked Jul 2026."),
    "ftc2013-03": published("RAND Journal of Economics", 2019, "Sequential Innovation, Patent Policy, and the Dynamics of the Replacement Effect", "https://doi.org/10.1111/1756-2171.12287", "Same Álvaro Parra sequential-innovation project, published under an expanded title. Rechecked Jul 2026."),
    "ftc2013-10": published("Management Science", 2020, "Persuasion Through Selective Disclosure: Implications for Marketing, Campaigning, and Privacy Regulation", "https://doi.org/10.1287/mnsc.2019.3455", "The published paper states that it supersedes the earlier 'Hypertargeting, Limited Attention, and Privacy' version. Rechecked Jul 2026."),
    "ftc2014-08": published("Review of Economic Studies", 2019, "Ask Your Doctor? Direct-to-Consumer Advertising of Pharmaceuticals", "https://doi.org/10.1093/restud/rdy001", "Michael Sinkinson's current research page identifies this as the published version of the prescription-drug consumer-advertising project. Rechecked Jul 2026."),
    "ftc2015-01": published("Journal of Finance", 2018, "Anticompetitive Effects of Common Ownership", "https://doi.org/10.1111/jofi.12698", "Exact project match; punctuation normalized in the published title. Rechecked Jul 2026 and synchronized with the Northwestern appearance."),
    "ftc2015-05": rr("AEJ: Microeconomics", "https://econ.la.psu.edu/wp-content/uploads/sites/5/2022/01/MyCV-9.pdf", "Paul Grieco's last located CV explicitly lists 'Generalized Insurer Bargaining' as revise and resubmit at American Economic Journal: Microeconomics (February 2018 version; CV posted 2019). No later publication was found; classified from the last explicit author-reported status, rechecked Jul 2026."),
    "ftc2015-06": published("Management Science", 2019, "Controlling vs. Enabling", "https://doi.org/10.1287/mnsc.2017.2956", "Same Hagiu-Wright project, published with the title order reversed and wording shortened. Rechecked Jul 2026."),
    "ftc2015-09": published("Review of Economic Studies", 2019, "Externalities and Benefit Design in Health Insurance", "https://doi.org/10.1093/restud/rdz052", "Same Amanda Starc health-insurance benefit-design project, published under a revised title. Rechecked Jul 2026."),
    "ftc2016-09": published("International Journal of Industrial Organization", 2019, "Innovation and Competition: The Role of the Product Market", "https://doi.org/10.1016/j.ijindorg.2019.04.001", "Same Álvaro Parra innovation-and-product-market-competition project, published under a revised title. Rechecked Jul 2026."),
    "ftc2017-01": published("RAND Journal of Economics", 2020, "Intermediaries and Product Quality in Used Car Markets", "https://doi.org/10.1111/1756-2171.12344", "Same Murry-Zhou used-car intermediary project, published under a revised title. Rechecked Jul 2026."),
    "ftc2017-03": published("RAND Journal of Economics", 2021, "Free Ad(vice): Internet Influencers and Disclosure Regulation", "https://doi.org/10.1111/1756-2171.12359", "Same internet-influencer advertising-advice project, published under an expanded title. Rechecked Jul 2026."),
    "ftc2017-06": published("American Economic Review", 2020, "The Competitive Impact of Vertical Integration by Multiproduct Firms", "https://doi.org/10.1257/aer.20180071", "Same Luco-Marshall vertical-integration project, published under a revised title. Rechecked Jul 2026 and synchronized with the Northwestern appearance."),
    "ftc2017-08": published("American Economic Review", 2019, "(Mis)Allocation, Market Power, and Global Oil Extraction", "https://doi.org/10.1257/aer.20171438", "Allan Collard-Wexler's research page identifies the AER article as the published version of the world-oil/OPEC project. Rechecked Jul 2026."),
    "ftc2019-08": published("Review of Economics and Statistics", 2023, "Markups and Fixed Costs in Generic and Off-Patent Pharmaceutical Markets", "https://doi.org/10.1162/rest_a_01130", "Same Ganapati-McKibbin generic-pharmaceutical project, published under a revised title. Rechecked Jul 2026."),
    "ftc2020-04": published("AEJ: Economic Policy", 2026, "Vertical Integration and Cream Skimming of Profitable Referrals: The Case of Hospital-Owned Skilled Nursing Facilities", "https://doi.org/10.1257/pol.20200892", "Leemore Dafny's April 2026 CV lists the article among refereed publications; same hospital-owned skilled-nursing-facility project. Rechecked Jul 2026."),
    "ftc2021-01": published("Journal of Marketing Research", 2023, "Debunking Misinformation About Consumer Products: Effects on Beliefs and Purchase Behavior", "https://doi.org/10.1177/00222437221147088", "Same Jessica Fong advertising-misinformation project, published under an expanded title. Rechecked Jul 2026."),
    "ftc2022-03": published("Journal of Health Economics", 2023, "Private Equity and Healthcare Firm Behavior: Evidence from Ambulatory Surgery Centers", "https://doi.org/10.1016/j.jhealeco.2023.102801", "Same Michael Richards healthcare-firm-behavior project, published under an expanded title. Rechecked Jul 2026."),
    "ftc2023-06": rr("Journal of Political Economy", "https://www.parker-rogers.com/research", "Parker Rogers' current research page lists the paper as revise and resubmit at the Journal of Political Economy. This supersedes an older author CV that reported an earlier reject-and-resubmit elsewhere. Rechecked Jul 2026."),
    "ftc2023-08": published("Marketing Science", 2022, "The Market for Fake Reviews", "https://doi.org/10.1287/mksc.2022.1353", "Same Hollenbeck-Mozaffar fake-review welfare project, published under a shortened title before its FTC presentation. Rechecked Jul 2026."),
    "ftc2024-01": rr("International Journal of Industrial Organization", "https://yanyouchen.com/research/", "Yanyou Chen's current research page says 'Revision requested at IJIO' for this paper. Classified as R&R at the named journal; rechecked Jul 2026."),
    "ftc2024-02": rr("Econometrica", "https://sites.google.com/site/gregorjarosch/research", "Gregor Jarosch's current research page lists 'Dynamic Monopsony with Granular Firms' as R&R at Econometrica (March 2026 version). Rechecked Jul 2026."),
    "ftc2026-05": published("Management Science", None, None, "https://tesarylin.github.io/research/dark-pattern/", "Tesary Lin's current research page and May 2026 CV list 'Designing Consent' as accepted at Management Science. Accepted is reported as published under the dashboard taxonomy; no issue year yet. Rechecked Jul 2026."),
    "nwae2012-04": published("Journal of Economic Theory", 2018, "Exclusive Dealing and Vertical Integration in Interlocking Relationships", "https://doi.org/10.1016/j.jet.2018.06.003", "Same Nocke-Rey vertical-integration/foreclosure project, published under a revised title. Rechecked Jul 2026."),
    "nwae2012-06": published("RAND Journal of Economics", 2025, "A Dynamic Model of Predation", "https://doi.org/10.1111/1756-2171.70027", "The long-running predation project was published under the same title; the final author list evolved before publication. Author/publication trail rechecked Jul 2026."),
    "nwae2013-05": published("Antitrust Law Journal", 2014, None, "https://www.crai.com/insights-events/publications/strategic-patent-acquisitions/", "Exact-title Shapiro-Scott Morton article published in Antitrust Law Journal 79(2), 463-499. Author/publication record rechecked Jul 2026."),
    "nwae2013-07": published("Journal of Economic Theory", 2017, "All-Units Discounts and Double Moral Hazard", "https://doi.org/10.1016/j.jet.2017.02.001", "Exact Daniel O'Brien project, with title capitalization normalized. Rechecked Jul 2026."),
    "nwae2013-08": published("Econometrica", 2018, "The Welfare Effects of Vertical Integration in Multichannel Television Markets", "https://doi.org/10.3982/ECTA14031", "Same multichannel-television vertical-integration project and author team, published under a revised title. Rechecked Jul 2026."),
    "nwae2014-02": published("Antitrust Law Journal", 2016, None, "https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2715997", "Jonathan Baker's current CV lists the exact-title article in Antitrust Law Journal 80, 431-461. Rechecked Jul 2026."),
    "nwae2014-09": published("Review of Industrial Organization", 2016, "Exclusionary Conduct of Dominant Firms, R&D Competition, and Innovation", "https://doi.org/10.1007/s11151-015-9485-9", "Jonathan Baker's current CV identifies the Review of Industrial Organization article as the published version of this project. Rechecked Jul 2026."),
    "nwae2015-03": published("American Economic Review", 2021, "Oligopolistic Price Leadership and Mergers: The United States Beer Industry", "https://doi.org/10.1257/aer.20190913", "The Miller-Weinberg beer-merger/tacit-collusion project evolved into the AER article, with Gloria Sheu added and the title revised. Author/publication trail rechecked Jul 2026."),
    "nwae2015-04": published("Harvard Law Review", 2017, None, "https://harvardlawreview.org/print/vol-130/on-the-relevance-of-market-power/", "Exact-title Louis Kaplow article published in Harvard Law Review 130, 1303-1407. Rechecked Jul 2026."),
    "nwae2015-05": published("Journal of Finance", 2018, "Anticompetitive Effects of Common Ownership", "https://doi.org/10.1111/jofi.12698", "Exact project match; punctuation normalized in the published title. Rechecked Jul 2026 and synchronized with the FTC appearance."),
    "nwae2015-07": published("International Journal of Industrial Organization", 2017, "Strategic Incentives When Supplying to Rivals with an Application to Vertical Firm Structure", "https://doi.org/10.1016/j.ijindorg.2016.12.005", "Same Schwartz-Moresi supplying-to-rivals project, published under an expanded title. Rechecked Jul 2026."),
    "nwae2016-02": published("Antitrust Law Journal", 2017, None, "https://www.jstor.org/stable/26425590", "Exact-title Abrahamson-Scott Morton article published in Antitrust Law Journal 81(3), 777-836. Rechecked Jul 2026."),
    "nwae2017-05": published("Antitrust Law Journal", 2017, None, "https://www.jstor.org/stable/26425585", "Exact-title Posner-Scott Morton-Weyl article published in Antitrust Law Journal 81, 669-728. Rechecked Jul 2026."),
    "nwae2017-08": published("American Economic Review", 2020, "The Competitive Impact of Vertical Integration by Multiproduct Firms", "https://doi.org/10.1257/aer.20180071", "Same Luco-Marshall vertical-integration project, published under a revised title. Rechecked Jul 2026 and synchronized with the FTC appearance."),
    "nwae2018-03": published("Journal of Law and Economics", 2021, "Coordinated Effects in Merger Review", "https://doi.org/10.1086/714919", "Same Loertscher-Marx coordinated-effects project, published under an expanded title. Rechecked Jul 2026."),
    "nwae2018-06": published("Harvard Law Review", 2018, None, "https://harvardlawreview.org/print/vol-132/antitrust-remedies-for-labor-market-power/", "Exact-title Naidu-Posner-Weyl article published in Harvard Law Review 132, 536-601. Rechecked Jul 2026."),
    "nwae2019-04": published("Yale Law Journal", 2020, None, "https://www.yalelawjournal.org/article/the-strategies-of-anticompetitive-common-ownership", "Exact-title Hemphill-Kahan article published in Yale Law Journal 129, 1392-1459. Rechecked Jul 2026."),
    "nwae2023-05": published("American Economic Review: Insights", 2024, None, "https://doi.org/10.1257/aeri.20230340", "Exact-title Brot-Goldberg-Cooper-Craig-Klarnet publication. Rechecked Jul 2026."),
    "nwae2023-07": published("Journal of Political Economy Microeconomics", None, None, "https://www.lucamaini.com/research", "Luca Maini's current research page and April 2026 CV list 'Mergers that Matter' as accepted at Journal of Political Economy Microeconomics. Accepted is reported as published; no issue year yet. Rechecked Jul 2026."),
    "nwae2024-03": rr("American Economic Review", "https://sites.google.com/view/thomaswollmann", "Thomas Wollmann's current research page lists 'Painful Bargaining' as revise and resubmit at the American Economic Review (May 2026). Rechecked Jul 2026."),
    "nwae2024-05": published("Journal of Political Economy", None, None, "https://sites.google.com/view/eprager/research", "Elena Prager's current research page lists 'Collusion through Common Leadership' as accepted at the Journal of Political Economy. Accepted is reported as published; no issue year yet. Rechecked Jul 2026."),
}


def main():
    rows = json.loads(LOOKUP.read_text())
    by_id = {row["id"]: row for row in rows}
    missing = sorted(set(OVERRIDES) - set(by_id))
    if missing:
        raise SystemExit(f"IDs missing from batch 30: {', '.join(missing)}")

    for pid, changes in OVERRIDES.items():
        existing = by_id[pid].get("status")
        if existing not in ("working_paper", changes["status"]):
            raise SystemExit(f"Refusing to override conflicting record {pid}: {existing}")
        by_id[pid].update(changes)

    stale = "conservatively classified as a working paper pending CV review."
    replacement = (
        "Author CV/research-page and exact-title publication checks found no publication, "
        "acceptance, or named-journal revise-and-resubmit as of 14 Jul 2026; retained as a "
        "working paper. 'Under review' and unnamed R&Rs do not qualify as R&R here."
    )
    for row in rows:
        if row.get("status") == "working_paper" and stale in (row.get("note") or ""):
            row["note"] = replacement

    LOOKUP.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n")
    print(f"Applied {len(OVERRIDES)} reviewed overrides to {LOOKUP}")


if __name__ == "__main__":
    main()
