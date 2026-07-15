#!/usr/bin/env python3
"""Apply structured tranche decisions from the exhaustive renamed-title audit."""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from pathlib import Path

from audit_nber_si_cvs import match_norm


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "nber_si" / "data"
REVIEWED_CANDIDATE_SNAPSHOT = "0cb6f20be31262ad0f14b25fc059311f0f8c5557f87207c80fc51fdaf60dc5ea"
REVIEWED_TOP5_FOLLOWUP_SNAPSHOT = "b244e4ed0dbb029ab790e82f98934fb15568c5d57172ab88afee676b03821ad4"
TOP5 = {
    "American Economic Review",
    "Quarterly Journal of Economics",
    "Journal of Political Economy",
    "Econometrica",
    "Review of Economic Studies",
}


def pair(paper_id: str, doi: str) -> tuple[str, str]:
    return paper_id, doi.lower()


HIGH_SIGNAL_ACCEPT = {
    pair(row["paper_id"], row["doi"])
    for row in json.loads((DATA / "high_signal_review_accept_pairs.json").read_text())
}


TOP5_REJECT = {
    pair("nbersi-2025-si-2025-development-american-economy-f220003", "10.1093/qje/qjaf046"),
    pair("nbersi-2017-si-2017-impulse-and-propagation-mechanisms-f93601", "10.1257/aer.20230983"),
    pair("nbersi-2018-si-2018-macroeconomics-within-and-across-borders-f114423", "10.1086/720139"),
    pair("nbersi-2018-si-2018-macroeconomics-within-and-across-borders-f114423", "10.1093/restud/rdae017"),
    pair("nbersi-2017-si-2017-aging-f93610", "10.1086/705716"),
    pair("nbersi-2015-si-2015-forecasting-empirical-methods-f81045", "10.1086/741624"),
    pair("nbersi-2022-si-2022-conference-research-income-and-wealth-f170917", "10.1093/restud/rdad016"),
    pair("nbersi-2024-si-2024-capital-markets-and-economy-f203333", "10.1086/726703"),
    pair("nbersi-2015-si-2015-development-economics-f81507", "10.1257/aer.p20151076"),
    pair("nbersi-2019-si-2019-economic-growth-f121889", "10.1257/aer.20171349"),
    pair("nbersi-2016-si-2016-health-care-f88117", "10.1257/aer.20151318"),
    pair("nbersi-2024-si-2024-monetary-economics-f206809", "10.3982/ecta21791"),
    pair("nbersi-2018-si-2018-macro-public-finance-f113862", "10.3982/ecta15088"),
    pair("nbersi-2015-si-2015-public-econ-taxation-social-insurance-f81581", "10.1093/restud/rdaa015"),
    pair("nbersi-2019-si-2019-corporate-finance-f121079", "10.1257/aer.113.7.2053"),
    pair("nbersi-2019-si-2019-corporate-finance-f121079", "10.1257/aer.20210369"),
    pair("nbersi-2018-si-2018-crime-f111024", "10.1086/705330"),
    pair("nbersi-2024-si-2024-forecasting-empirical-methods-f205949", "10.3982/ecta21654"),
    pair("nbersi-2018-si-2018-children-f108085", "10.1257/aer.20141406"),
    pair("nbersi-2016-si-2016-impulse-and-propagation-mechanisms-f87179", "10.1086/701608"),
    pair("nbersi-2021-si-2021-household-finance-f150434", "10.1093/restud/rdaf028"),
    pair("nbersi-2022-si-2022-monetary-economics-f172891", "10.1086/736211"),
    pair("nbersi-2017-si-2017-international-asset-pricing-f96543", "10.1086/705688"),
    pair("nbersi-2020-si-2020-macro-money-and-financial-markets-f142356", "10.1257/aer.20181830"),
    pair("nbersi-2015-si-2015-household-finance-meeting-f81460", "10.1093/qje/qjw001"),
    pair("nbersi-2016-si-2016-economics-education-f88471", "10.1086/728109"),
    pair("nbersi-2016-si-2016-labor-studies-f86628", "10.1257/aer.20190221"),
    pair("nbersi-2016-si-2016-nbercriw-workshop-f88954", "10.1257/aer.p20161020"),
    pair("nbersi-2017-si-2017-income-distribution-and-macroeconomics-f95534", "10.1093/restud/rdy027"),
    pair("nbersi-2018-si-2018-global-financial-crisis-10-f114470", "10.1093/restud/rdae070"),
    pair("nbersi-2018-si-2018-global-financial-crisis-10-f114470", "10.1257/aer.20170007"),
    pair("nbersi-2020-si-2020-development-economics-f144087", "10.3982/ecta17945"),
    pair("nbersi-2022-si-2022-macro-perspectives-f171693", "10.1257/aer.20191521"),
    pair("nbersi-2022-si-2022-macro-perspectives-f171693", "10.3982/ecta21466"),
    pair("nbersi-2023-si-2023-digital-economics-and-artificial-intelligence-f186588", "10.1093/restud/rdac056"),
    pair("nbersi-2024-si-2024-economics-social-security-f207107", "10.3982/ecta19021"),
    pair("nbersi-2024-si-2024-entrepreneurship-f207896", "10.1093/restud/rdae047"),
    pair("nbersi-2024-si-2024-international-trade-investment-f199524", "10.1086/726907"),
    pair("nbersi-2025-si-2025-economics-health-f219788", "10.1086/734134"),
    pair("nbersi-2025-si-2025-urban-economics-f215045", "10.1086/739335"),
    pair("nbersi-2026-si-2026-behavioral-macro-f241164", "10.1093/qje/qjag023"),
    pair("nbersi-2022-si-2022-micro-data-and-macro-models-f166016", "10.3982/ecta21045"),
    pair("nbersi-2018-si-2018-it-and-digitization-f104454", "10.1086/696229"),
}

NON_TOP5_REJECT = {
    pair("nbersi-2018-si-2018-monetary-economics-f112129", "10.1146/annurev-financial-111620-022146"),
    pair("nbersi-2025-si-2025-conference-research-income-and-wealth-f224187", "10.54254/2754-1169/2026.bl32621"),
    pair("nbersi-2017-si-2017-children-f97574", "10.3368/jhr.58.5.0520-10930r1"),
    pair("nbersi-2016-si-2016-forecasting-empirical-methods-f88543", "10.1016/j.jeconom.2020.05.004"),
    pair("nbersi-2018-si-2018-income-distribution-and-macroeconomics-f107439", "10.1038/s41586-023-06051-2"),
    pair("nbersi-2018-si-2018-income-distribution-and-macroeconomics-f107439", "10.1038/s41586-023-06886-9"),
    pair("nbersi-2015-si-2015-development-american-economy-f81099", "10.17016/2380-7172.1831"),
    pair("nbersi-2019-si-2019-urban-economics-f124001", "10.1007/s10887-019-09167-1"),
    pair("nbersi-2017-si-2017-macro-public-finance-f95381", "10.1016/j.jedc.2023.104737"),
    pair("nbersi-2015-si-2015-children-f81647", "10.1289/isee.2015.2015-739"),
    pair("nbersi-2024-si-2024-forecasting-empirical-methods-f201097", "10.1080/07350015.2024.2393722"),
    pair("nbersi-2016-si-2016-macro-perspectives-f88673", "10.4000/travailemploi.8996"),
    pair("nbersi-2015-si-2015-aggregate-implications-micro-f81446", "10.26509/frbc-ec-201509"),
    pair("nbersi-2024-si-2024-macro-public-finance-f208166", "10.1146/annurev-economics-091624-044646"),
    pair("nbersi-2015-si-2015-development-american-economy-f81303", "10.1257/pandp.20201090"),
    pair("nbersi-2026-si-2026-labor-studies-f242682", "10.1216/rmj.2026.56.221"),
    pair("nbersi-2026-si-2026-workshop-aging-f245818", "10.3390/agriculture16131478"),
}

MID_SCORE_REJECT = {
    pair("nbersi-2019-si-2019-health-economics-f119109", "10.1257/app.20210230"),
    pair("nbersi-2015-si-2015-aggregate-implications-micro-f79500", "10.1016/j.jpubeco.2020.104176"),
    pair("nbersi-2016-si-2016-development-american-economy-f88585", "10.18237/kdgw.2018.36.1.043"),
    pair("nbersi-2022-si-2022-economics-social-security-f171954", "10.1007/s00148-022-00915-z"),
    pair("nbersi-2024-si-2024-capital-markets-and-economy-f203333", "10.1086/729197"),
    pair("nbersi-2025-si-2025-impulse-and-propagation-mechanisms-f222154", "10.1086/735272"),
}

DUPLICATE_DOI_REJECT = {
    pair("nbersi-2019-si-2019-entrepreneurship-f124715", "10.1002/smj.70035"),
    pair("nbersi-2020-si-2020-international-finance-macroeconomics-f142351", "10.1016/j.jfineco.2023.07.003"),
    pair("nbersi-2019-si-2019-aging-f129777", "10.1016/j.jpubeco.2021.104478"),
    pair("nbersi-2020-si-2020-law-and-economics-f143169", "10.1016/j.jpubeco.2021.104478"),
    pair("nbersi-2017-si-2017-public-economics-f92332", "10.1016/j.jpubeco.2021.104557"),
    pair("nbersi-2022-si-2022-macro-perspectives-f169683", "10.1086/726632"),
    pair("nbersi-2024-si-2024-capital-markets-and-economy-f203333", "10.1086/726703"),
    pair("nbersi-2018-si-2018-real-estate-f110399", "10.1086/729197"),
    pair("nbersi-2024-si-2024-capital-markets-and-economy-f203333", "10.1086/729197"),
    pair("nbersi-2025-si-2025-impulse-and-propagation-mechanisms-f222154", "10.1086/735272"),
    pair("nbersi-2020-si-2020-monetary-economics-f138261", "10.1093/ectj/utaf022"),
    pair("nbersi-2023-si-2023-monetary-economics-f187595", "10.1093/ectj/utaf022"),
    pair("nbersi-2025-si-2025-labor-studies-f226683", "10.1093/qje/qjaf049"),
    pair("nbersi-2019-si-2019-behavioral-macro-f129387", "10.1162/rest_a_01566"),
    pair("nbersi-2020-si-2020-macro-money-and-financial-markets-f142356", "10.1257/aer.20181830"),
    pair("nbersi-2022-si-2022-conference-research-income-and-wealth-f170391", "10.1257/aer.20221574"),
    pair("nbersi-2022-si-2022-conference-research-income-and-wealth-f167429", "10.1257/mac.20200486"),
    pair("nbersi-2024-si-2024-forecasting-empirical-methods-f205949", "10.3982/ecta21654"),
}

HIGH_SIGNAL_REJECT = {
    pair("nbersi-2022-si-2022-economics-social-security-f171954", "10.1007/s00148-022-00915-z"),
    pair("nbersi-2019-si-2019-health-economics-f119109", "10.1257/app.20210230"),
    pair("nbersi-2020-si-2020-crime-f139004", "10.21428/cb6ab371.2c9ade4b"),
    pair("nbersi-2019-si-2019-political-economy-f123750", "10.1016/j.jce.2025.07.012"),
    pair("nbersi-2026-si-2026-macro-public-finance-f241358", "10.1093/ej/ueag006"),
    pair("nbersi-2020-si-2020-development-american-economy-f142503", "10.1257/app.20180299"),
    pair("nbersi-2019-si-2019-real-estate-f119778", "10.3982/qe1664"),
    pair("nbersi-2017-si-2017-behavioral-macro-f91764", "10.1016/j.jmoneco.2016.12.003"),
    pair("nbersi-2020-si-2020-risks-financial-institutions-f139836", "10.1287/mnsc.2022.00097"),
    pair("nbersi-2017-si-2017-development-american-economy-f96442", "10.1162/rest_a_00860"),
    pair("nbersi-2016-si-2016-real-estate-f88768", "10.1111/ssqu.12812"),
    pair("nbersi-2023-si-2023-aging-f188595", "10.1162/rest.a.265"),
    pair("nbersi-2022-si-2022-conference-research-income-and-wealth-f167971", "10.1093/qje/qjac039"),
    pair("nbersi-2025-si-2025-real-estate-f221502", "10.1080/13504851.2025.2560672"),
    pair("nbersi-2019-si-2019-macroeconomics-within-and-across-borders-f129805", "10.1093/restud/rdad058"),
    pair("nbersi-2021-si-2021-development-american-economy-f156886", "10.1016/j.eeh.2024.101616"),
    pair("nbersi-2019-si-2019-behavioral-macro-f129387", "10.1162/rest_a_01566"),
    pair("nbersi-2022-si-2022-political-economy-f170190", "10.1257/mic.20220146"),
    pair("nbersi-2016-si-2016-nbercriw-workshop-f88973", "10.17016/2380-7172.1885"),
    pair("nbersi-2015-si-2015-development-american-economy-f81303", "10.1177/0019793917726981"),
    pair("nbersi-2022-si-2022-monetary-economics-f171190", "10.1111/jmcb.12896"),
    pair("nbersi-2018-si-2018-forecasting-empirical-methods-f108835", "10.1016/j.jeconom.2018.05.004"),
}


def explicitly_rejected(identity: tuple[str, str]) -> bool:
    return identity in (TOP5_REJECT | NON_TOP5_REJECT | MID_SCORE_REJECT
                        | DUPLICATE_DOI_REJECT | HIGH_SIGNAL_REJECT)

PAIR_ACCEPT = {
    pair("nbersi-2020-si-2020-macro-money-and-financial-markets-f142356", "10.1016/j.jfineco.2023.07.003"),
}

MANUAL_RENAMED = [
    {
        "paper_id": "nbersi-2020-si-2020-risks-financial-institutions-f139836",
        "normalized_title": "too big to diversify",
        "title": "Too Big to Diversify",
        "status": "published",
        "journal": "Journal of Financial Economics",
        "pub_year": 2022,
        "published_title": "Fire-sale risk in the leveraged loan market",
        "url": "https://doi.org/10.1016/j.jfineco.2022.05.003",
        "evidence_url": "https://doi.org/10.1016/j.jfineco.2022.05.003",
        "reviewed_at": "2026-07-14",
        "evidence_source": "structured replacement DOI review",
        "note": "Author continuity and project details verify the renamed JFE article after rejecting a neighboring CLO paper.",
    },
    {
        "paper_id": "nbersi-2024-si-2024-forecasting-empirical-methods-f201097",
        "normalized_title": "imputation of counterfactual outcomes when the errors are predictable",
        "title": "Imputation of Counterfactual Outcomes when the Errors are Predictable",
        "status": "published",
        "journal": "Journal of Business & Economic Statistics",
        "pub_year": 2024,
        "published_title": "Imputation of Counterfactual Outcomes when the Errors are Predictable",
        "url": "https://doi.org/10.1080/07350015.2024.2358900",
        "evidence_url": "https://doi.org/10.1080/07350015.2024.2358900",
        "reviewed_at": "2026-07-14",
        "evidence_source": "structured replacement DOI review",
        "note": "Original JBES article verified after rejecting the separate rejoinder DOI.",
    },
    {
        "paper_id": "nbersi-2016-si-2016-macro-perspectives-f88673",
        "normalized_title": "job polarization and structural change",
        "title": "Job Polarization and Structural Change",
        "status": "published",
        "journal": "AEJ: Macroeconomics",
        "pub_year": 2018,
        "published_title": "Job Polarization and Structural Change",
        "url": "https://doi.org/10.1257/mac.20150258",
        "evidence_url": "https://doi.org/10.1257/mac.20150258",
        "reviewed_at": "2026-07-14",
        "evidence_source": "structured replacement DOI review",
        "note": "Exact-title AEJ: Macroeconomics record verified after rejecting a later survey article.",
    },
]

EXTRA_ACCEPT_DOIS = {
    "10.1016/j.jdeveco.2021.102811", "10.1073/pnas.2200841119", "10.1162/rest_a_01398",
    "10.1257/pol.20230052", "10.1162/rest_a_01248", "10.1257/pol.20210667",
    "10.1017/s1355770x20000224", "10.1287/mnsc.2019.03116", "10.1016/j.jdeveco.2025.103515",
    "10.1016/j.jue.2024.103734", "10.1093/jeea/jvaf018", "10.3368/jhr.0421-11584r1",
    "10.1162/rest_a_01565", "10.1016/j.jfineco.2025.104129", "10.1111/jofi.70046",
    "10.1016/j.jinteco.2024.103910", "10.1111/jofi.70001", "10.1162/rest_a_01275",
    "10.1093/ej/uead048", "10.1086/705682", "10.1162/rest_a_01151",
    "10.1016/j.jfineco.2022.07.006", "10.1016/j.jebo.2022.07.021", "10.1257/mac.20190019",
    "10.1561/108.00000022", "10.1093/ej/ueag009", "10.1111/jofi.12614",
    "10.1017/s0022109020000770", "10.1257/app.20200787", "10.1093/rfs/hhz009",
    "10.1016/j.jfineco.2021.06.004", "10.1257/app.20220483", "10.1016/j.jeconom.2024.105726",
    "10.1162/rest_a_01166", "10.1016/j.socscimed.2022.114762", "10.1162/rest_a_00833",
    "10.1086/728094", "10.1086/714439", "10.1016/j.jeconom.2025.106055",
    "10.1257/app.20230365", "10.1257/app.20220512", "10.1287/mnsc.2020.3650",
    "10.1016/j.jeconom.2023.105634", "10.1007/s13524-020-00882-8", "10.1007/s10887-025-09252-8",
    "10.1016/j.jmoneco.2023.08.001", "10.1257/pol.20210399", "10.1257/pol.20170474",
    "10.1257/app.20190772", "10.1093/jeea/jvac058", "10.1257/app.20220400",
    "10.1287/mnsc.2018.3084", "10.1016/j.jpubeco.2024.105179", "10.1016/j.jinteco.2026.104255",
    "10.1038/s41586-024-07945-5", "10.1287/mnsc.2017.2875", "10.1093/rfs/hhz098",
    "10.1016/j.jet.2024.105940", "10.1002/jae.70004", "10.1111/jofi.13383",
    "10.1016/j.jhealeco.2024.102860", "10.1111/iere.12447", "10.1111/1756-2171.12269",
    "10.1257/pandp.20261042", "10.17310/ntj.2019.3.01", "10.1162/rest_a_01218",
}


def key(row: dict) -> str:
    raw = "|".join(str(row.get(field) or "") for field in (
        "paper_id", "candidate_status", "candidate_title", "journal", "doi", "evidence_url", "url"
    ))
    return hashlib.sha1(raw.encode()).hexdigest()


def normalized_doi(row: dict) -> str:
    return (row.get("doi") or "").lower().removeprefix("https://doi.org/")


def accepted_reason(row: dict, reviewed_snapshot: bool,
                    reviewed_top5_followup_snapshot: bool) -> str | None:
    doi = normalized_doi(row)
    identity = pair(row["paper_id"], doi)
    if explicitly_rejected(identity):
        return None
    title_key = (row.get("candidate_title") or "").casefold()
    if row.get("journal", "").casefold() == "isee conference abstracts":
        return None
    if any(term in title_key for term in ("corrigendum", "author correction", "retraction", "retracted", "reply", "comment")):
        return None
    if identity in PAIR_ACCEPT:
        return "structured review: author set, publication abstract, and draft text confirm the renamed project lineage"
    if identity in HIGH_SIGNAL_ACCEPT:
        return "structured high-signal review: OpenAlex abstract and title-lineage evidence confirm the renamed project"
    if reviewed_top5_followup_snapshot and row.get("journal") in TOP5:
        return "structured follow-up review: exact coauthor query and title-lineage evidence confirm the Top-5 publication"
    if doi in EXTRA_ACCEPT_DOIS:
        return "structured review: exact author set, post-conference DOI, and confirmed semantic project lineage"
    if reviewed_snapshot and (
        (row.get("distinctive_term_coverage") or 0) >= 0.667
        or (row.get("title_ratio") or 0) >= 0.75
    ):
        return "structured review: exact author set, post-conference DOI, and strong distinctive-title continuity"
    if reviewed_snapshot and ((row.get("distinctive_term_coverage") or 0) >= 0.6
                              or (row.get("title_ratio") or 0) >= 0.6):
        return "structured tranche review: exact author set, post-conference DOI, and confirmed project continuity"
    return None


def publication_record(candidate: dict, reason: str) -> dict:
    doi = normalized_doi(candidate)
    journal = candidate["journal"]
    # Crossref sometimes files AER Papers & Proceedings under the parent AER
    # title. Keep it published, but do not inflate flagship Top-5 placement.
    if doi.startswith("10.1257/aer.p"):
        journal = "AEA Papers & Proceedings"
    return {
        "paper_id": candidate["paper_id"],
        "normalized_title": match_norm(candidate["agenda_title"]),
        "title": candidate["agenda_title"],
        "status": "published",
        "journal": journal,
        "pub_year": candidate.get("candidate_year"),
        "published_title": candidate["candidate_title"],
        "url": candidate.get("url") or ("https://doi.org/" + doi if doi else None),
        "evidence_url": candidate.get("url") or ("https://doi.org/" + doi if doi else None),
        "reviewed_at": "2026-07-14",
        "evidence_source": "exhaustive renamed-lineage tranche review",
        "note": reason + ". Cross-checked July 2026.",
    }


def main() -> None:
    papers = json.loads((DATA / "papers_enriched.json").read_text())
    by_id = {row["id"]: row for row in papers}
    candidate_path = DATA / "renamed_lineage_candidates.json"
    candidates = json.loads(candidate_path.read_text())
    reviewed_snapshot = hashlib.sha256(candidate_path.read_bytes()).hexdigest() == REVIEWED_CANDIDATE_SNAPSHOT
    reviewed_top5_followup_snapshot = hashlib.sha256(candidate_path.read_bytes()).hexdigest() == REVIEWED_TOP5_FOLLOWUP_SNAPSHOT
    confirmed_path = DATA / "renamed_lineage_confirmed.json"
    previous_confirmed = json.loads(confirmed_path.read_text())
    prior_exhaustive_ids = {row["paper_id"] for row in previous_confirmed
                            if row.get("evidence_source") == "exhaustive renamed-lineage tranche review"}
    confirmed = [row for row in previous_confirmed
                 if row.get("evidence_source") != "exhaustive renamed-lineage tranche review"]
    confirmed_by_paper = {row["paper_id"]: row for row in confirmed}
    confirmed_by_paper.update({row["paper_id"]: row for row in MANUAL_RENAMED})
    decision_path = DATA / "exhaustive_candidate_decisions.json"
    decisions = json.loads(decision_path.read_text()) if decision_path.exists() else {}
    # A prior coordinator version accidentally treated author overlap as abstract
    # similarity. Remove those temporary decisions; reviewed semantic decisions
    # are applied only from an exact pair manifest.
    decisions = {
        decision_key: decision for decision_key, decision in decisions.items()
        if decision.get("reason") != "structured high-signal review: author continuity and post-conference semantic project match"
    }

    accepted_by_paper = defaultdict(list)
    accepted_rows = rejected_rows = 0
    for candidate in candidates:
        paper = by_id.get(candidate.get("paper_id"))
        prior_decision = decisions.get(key(candidate), {}).get("state")
        if not paper or (paper.get("status") != "working_paper"
                         and candidate.get("paper_id") not in prior_exhaustive_ids
                         and prior_decision != "accepted"):
            continue
        identity = pair(candidate["paper_id"], normalized_doi(candidate))
        reason = None if explicitly_rejected(identity) else (
            decisions.get(key(candidate), {}).get("reason")
            if prior_decision == "accepted"
            else accepted_reason(candidate, reviewed_snapshot, reviewed_top5_followup_snapshot)
        )
        if reason:
            decisions[key(candidate)] = {
                "state": "accepted", "reason": reason, "paper_id": candidate["paper_id"],
                "doi": normalized_doi(candidate), "reviewed_at": "2026-07-14",
            }
            accepted_by_paper[candidate["paper_id"]].append((candidate, reason))
            accepted_rows += 1
        elif (explicitly_rejected(identity)
              or candidate.get("journal", "").casefold() == "isee conference abstracts"
              or any(term in (candidate.get("candidate_title") or "").casefold()
                     for term in ("corrigendum", "author correction", "retraction", "retracted", "reply", "comment"))):
            decisions[key(candidate)] = {
                "state": "rejected", "reason": "structured review found a separate, nonqualifying, or adjacent project",
                "paper_id": candidate["paper_id"], "doi": normalized_doi(candidate),
                "reviewed_at": "2026-07-14",
            }
            rejected_rows += 1

    added = 0
    for paper_id, options in accepted_by_paper.items():
        if (paper_id in confirmed_by_paper
                and confirmed_by_paper[paper_id].get("evidence_source") != "exhaustive renamed-lineage tranche review"):
            continue
        candidate, reason = max(options, key=lambda item: (
            item[0].get("journal") in TOP5,
            item[0].get("distinctive_term_coverage") or 0,
            item[0].get("title_ratio") or 0,
        ))
        replacing = paper_id in confirmed_by_paper
        confirmed_by_paper[paper_id] = publication_record(candidate, reason)
        if not replacing:
            added += 1

    confirmed_path.write_text(json.dumps(list(confirmed_by_paper.values()), indent=2, ensure_ascii=False) + "\n")
    decision_path.write_text(json.dumps(decisions, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({
        "accepted_candidate_rows": accepted_rows,
        "rejected_candidate_rows": rejected_rows,
        "new_confirmed_lineages": added,
        "total_confirmed_lineages": len(confirmed_by_paper),
        "terminal_candidate_decisions": len(decisions),
    }, indent=2))


if __name__ == "__main__":
    main()
