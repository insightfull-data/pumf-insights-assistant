"""Generate a small synthetic survey release shaped like a StatCan CIUS PUMF.

Everything here is invented. Variable codes follow PUMF conventions (fixed-width file,
SPSS syntax, 6/7/8/9 missing codes, a final weight plus bootstrap weights) so the same
ingest code can read a real PUMF, but no value comes from Statistics Canada.

Run:  python -m pumfai generate-data
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

RELEASE_ID = "cius_synth_2022"
DATA_FILE = "CIUS_SYNTH_2022.txt"
SYNTAX_FILE = "CIUS_SYNTH_2022.sps"
N_BOOT = 50
SEED = 20221

# Province: SGC code, abbreviation, invented population 15+ (rounded, millions), sample size
PROVINCES = [
    (10, "NL", "Newfoundland and Labrador", 0.44, 300),
    (11, "PE", "Prince Edward Island", 0.14, 200),
    (12, "NS", "Nova Scotia", 0.85, 400),
    (13, "NB", "New Brunswick", 0.67, 350),
    (24, "QC", "Quebec", 7.30, 1100),
    (35, "ON", "Ontario", 12.60, 1500),
    (46, "MB", "Manitoba", 1.10, 400),
    (47, "SK", "Saskatchewan", 0.93, 350),
    (48, "AB", "Alberta", 3.70, 650),
    (59, "BC", "British Columbia", 4.60, 750),
]
AGE_LABELS = ["15 to 24 years", "25 to 34 years", "35 to 44 years", "45 to 54 years", "55 to 64 years", "65 years and over"]
AGE_BANDS = ["15-24", "25-34", "35-44", "45-54", "55-64", "65+"]
AGE_SHARE = [0.15, 0.17, 0.16, 0.15, 0.16, 0.21]

# name, start, width, decimals, label
LAYOUT: list[tuple[str, int, int, int, str]] = []


def _layout():
    if LAYOUT:
        return LAYOUT
    cols = [
        ("PUMFID", 5, 0, "Public use microdata file identifier"),
        ("PROVINCE", 2, 0, "Province of residence"),
        ("AGE_GRP", 1, 0, "Age group of respondent"),
        ("GENDER", 1, 0, "Gender of respondent"),
        ("HHINCQ", 1, 0, "Household income quintile"),
        ("EDU", 1, 0, "Highest level of education completed"),
        ("UI_010", 1, 0, "Used the Internet in the past 12 months"),
        ("FQ_010", 1, 0, "Frequency of Internet use"),
        ("AC_STRM", 1, 0, "Watched video content online through a streaming service"),
        ("AC_POD", 1, 0, "Listened to podcasts"),
        ("AC_MUS", 1, 0, "Listened to music through a streaming service"),
        ("AC_NEWS", 1, 0, "Read or watched news online"),
        ("AC_SHOP", 1, 0, "Ordered goods or services online"),
        ("EC_SPND", 1, 0, "Total amount spent on online orders"),
        ("SM_USE", 1, 0, "Used social networking sites or apps"),
        ("DV_SMART", 1, 0, "Has a smartphone for personal use"),
        ("WTPP", 12, 4, "Final person weight"),
    ] + [(f"WTBS_{b:03d}", 12, 4, f"Bootstrap weight {b}") for b in range(1, N_BOOT + 1)]
    pos = 1
    for name, width, dec, label in cols:
        LAYOUT.append((name, pos, width, dec, label))
        pos += width
    return LAYOUT


YESNO = {1: "Yes", 2: "No"}
MISS = {6: "Valid skip", 7: "Don't know", 8: "Refusal", 9: "Not stated"}

VALUE_LABELS = {
    "PROVINCE": {p[0]: p[2] for p in PROVINCES},
    "AGE_GRP": {i + 1: lab for i, lab in enumerate(AGE_LABELS)},
    "GENDER": {1: "Men+", 2: "Women+"},
    "HHINCQ": {1: "Lowest quintile", 2: "Second quintile", 3: "Third quintile", 4: "Fourth quintile",
               5: "Highest quintile", 9: "Not stated"},
    "EDU": {1: "High school or less", 2: "College, CEGEP or trades", 3: "University degree", 9: "Not stated"},
    "UI_010": {**YESNO, 9: "Not stated"},
    "FQ_010": {1: "Several times a day", 2: "About once a day", 3: "At least once a week",
               4: "Less than once a week", **MISS},
    "AC_STRM": {**YESNO, **MISS}, "AC_POD": {**YESNO, **MISS}, "AC_MUS": {**YESNO, **MISS},
    "AC_NEWS": {**YESNO, **MISS}, "AC_SHOP": {**YESNO, **MISS}, "SM_USE": {**YESNO, **MISS},
    "EC_SPND": {1: "Less than $100", 2: "$100 to $499", 3: "$500 to $999", 4: "$1,000 or more", **MISS},
    "DV_SMART": {**YESNO, 9: "Not stated"},
}
MISSING_RANGES = {
    "HHINCQ": [9], "EDU": [9], "UI_010": [9], "DV_SMART": [9],
    "FQ_010": [6, 7, 8, 9], "AC_STRM": [6, 7, 8, 9], "AC_POD": [6, 7, 8, 9], "AC_MUS": [6, 7, 8, 9],
    "AC_NEWS": [6, 7, 8, 9], "AC_SHOP": [6, 7, 8, 9], "SM_USE": [6, 7, 8, 9], "EC_SPND": [6, 7, 8, 9],
}


def _by_age(rng, age_idx, probs, inc=None, inc_effect=0.0):
    p = np.asarray(probs)[age_idx]
    if inc is not None:
        q = np.where(inc == 9, 3, inc)
        p = p + inc_effect * (q - 3)
    return rng.random(len(age_idx)) < np.clip(p, 0.01, 0.99)


def generate(out_dir: Path) -> Path:
    rng = np.random.default_rng(SEED)
    rel = out_dir / "raw" / RELEASE_ID
    rel.mkdir(parents=True, exist_ok=True)

    prov, w = [], []
    for code, _, _, pop_m, n in PROVINCES:
        prov += [code] * n
        raw = rng.lognormal(0, 0.35, n)
        w += list(raw / raw.sum() * pop_m * 1e6)  # rake to province total
    prov = np.array(prov)
    w = np.array(w)
    n = len(prov)

    age_idx = rng.choice(6, n, p=AGE_SHARE)
    gender = rng.choice([1, 2], n, p=[0.49, 0.51])
    inc = rng.choice([1, 2, 3, 4, 5, 9], n, p=[0.196, 0.196, 0.196, 0.196, 0.196, 0.02])
    edu = np.where(rng.random(n) < 0.01, 9, 1 + (rng.random(n) < np.array([.45, .6, .62, .58, .52, .45])[age_idx]).astype(int)
                   + (rng.random(n) < np.array([.15, .45, .45, .38, .3, .25])[age_idx]).astype(int))
    edu = np.clip(edu, 1, 9)

    users = _by_age(rng, age_idx, [.99, .99, .98, .97, .94, .80], inc, 0.01)
    ui = np.where(users, 1, 2)
    ui[rng.random(n) < 0.005] = 9
    is_user = ui == 1

    fq = rng.choice([1, 2, 3, 4], n, p=[.62, .2, .13, .05])
    fq = np.where(age_idx >= 5, np.minimum(fq + rng.choice([0, 1], n, p=[.6, .4]), 4), fq)
    fq = np.where(is_user, fq, 6)

    def activity(probs, inc_eff=0.0):
        yes = _by_age(rng, age_idx, probs, inc, inc_eff)
        v = np.where(yes, 1, 2)
        v[rng.random(n) < 0.01] = 9
        return np.where(is_user, v, 6)

    strm = activity([.85, .82, .78, .70, .58, .42], 0.03)
    pod = activity([.45, .48, .42, .33, .22, .12], 0.02)
    mus = activity([.80, .72, .62, .50, .36, .20], 0.02)
    news = activity([.60, .68, .72, .74, .74, .70], 0.03)
    shop = activity([.78, .85, .84, .80, .72, .56], 0.05)
    sm = activity([.95, .90, .84, .76, .65, .48], 0.0)
    q = np.where(inc == 9, 3, inc)
    spend = np.clip(rng.choice([1, 2, 3, 4], n, p=[.25, .4, .2, .15]) + (rng.random(n) < 0.12 * (q - 1)).astype(int), 1, 4)
    spend = np.where(shop == 1, spend, np.where(shop == 9, 9, 6))
    smart = np.where(_by_age(rng, age_idx, [.97, .97, .96, .94, .88, .70], inc, 0.01), 1, 2)
    smart[rng.random(n) < 0.005] = 9

    # Bootstrap weights: Rao-Wu style resampling of n-1 units within each province stratum
    boots = np.zeros((n, N_BOOT))
    for code in np.unique(prov):
        idx = np.where(prov == code)[0]
        m = len(idx)
        for b in range(N_BOOT):
            draws = rng.multinomial(m - 1, np.full(m, 1 / m))
            boots[idx, b] = w[idx] * draws * m / (m - 1)
    boots = np.maximum(boots, 0)

    cols = {
        "PUMFID": np.arange(1, n + 1), "PROVINCE": prov, "AGE_GRP": age_idx + 1, "GENDER": gender,
        "HHINCQ": inc, "EDU": edu, "UI_010": ui, "FQ_010": fq, "AC_STRM": strm, "AC_POD": pod,
        "AC_MUS": mus, "AC_NEWS": news, "AC_SHOP": shop, "EC_SPND": spend, "SM_USE": sm,
        "DV_SMART": smart, "WTPP": w,
    }
    for b in range(N_BOOT):
        cols[f"WTBS_{b + 1:03d}"] = boots[:, b]

    lines = []
    lay = _layout()
    for i in range(n):
        parts = []
        for name, _, width, dec, _ in lay:
            v = cols[name][i]
            parts.append(f"{v:{width}.{dec}f}" if dec else f"{int(v):>{width}d}")
        lines.append("".join(parts))
    (rel / DATA_FILE).write_text("\n".join(lines) + "\n")
    (rel / SYNTAX_FILE).write_text(_spss_syntax())
    (rel / "steward_overlay.json").write_text(json.dumps(_overlay(), indent=1))
    guide = {
        "release_id": RELEASE_ID, "survey": "cius", "ref_period": "2022",
        "title": "Synthetic Internet Use Survey 2022 (CIUS-style, invented data)",
        "record_count": int(n), "weight_variable": "WTPP",
        "weight_total": round(float(w.sum()), 1), "bootstrap_prefix": "WTBS_", "n_bootstrap": N_BOOT,
        "reliability": {"caution_cv_pct": 16.6, "suppress_cv_pct": 33.3, "min_unweighted_n": 30},
        "population": "Persons aged 15 and over in the ten provinces (synthetic)",
        "licence": "Synthetic data generated for this repository; MIT licence. Not Statistics Canada data.",
    }
    (rel / "user_guide.json").write_text(json.dumps(guide, indent=1))
    return rel


def _spss_syntax() -> str:
    lay = _layout()
    out = [f"* Synthetic CIUS-style PUMF. Invented data; not Statistics Canada.", "",
           f"DATA LIST FILE='{DATA_FILE}' /"]
    for name, start, width, dec, _ in lay:
        end = start + width - 1
        out.append(f"  {name} {start}-{end}" + (f" ({dec})" if dec else ""))
    out.append(".\n\nVARIABLE LABELS")
    for name, _, _, _, label in lay:
        out.append(f'  {name} "{label}"')
    out.append(".\n\nVALUE LABELS")
    first = True
    for var, labs in VALUE_LABELS.items():
        out.append(("  " if first else "  /") + var)
        first = False
        for k, v in labs.items():
            out.append(f'    {k} "{v}"')
    out.append(".\n")
    for var, codes in MISSING_RANGES.items():
        out.append(f"MISSING VALUES {var} ({min(codes)} THRU {max(codes)})." if len(codes) > 1
                   else f"MISSING VALUES {var} ({codes[0]}).")
    out.append("\nEXECUTE.\n")
    return "\n".join(out)


def _overlay() -> dict:
    """Metadata a data steward adds on top of the syntax file: topics, universes, synonyms."""
    users = {"var": "ui_010", "eq": 1}
    act = lambda q, syn, desc: {"topic": "online_activities.past_3_months", "question_text": q,
                                "universe_expr": users, "universe_text": "Internet users in the past 12 months",
                                "synonyms": syn, "description": desc}
    return {
        "variables": {
            "province": {"topic": "geography", "synonyms": ["province", "region"], "measure_type": "categorical"},
            "age_grp": {"topic": "demographics", "synonyms": ["age", "age group"]},
            "gender": {"topic": "demographics", "synonyms": ["gender", "men", "women", "sex"]},
            "hhincq": {"topic": "demographics.income", "synonyms": ["income", "household income", "affluent", "low income"]},
            "edu": {"topic": "demographics.education", "synonyms": ["education", "degree", "university", "college"]},
            "ui_010": {"topic": "internet_use", "question_text": "In the past 12 months, have you used the Internet?",
                       "synonyms": ["internet users", "online", "uses the internet"], "description": "Whether the person used the Internet at all in the past 12 months."},
            "fq_010": {"topic": "internet_use", "question_text": "How often did you use the Internet?",
                       "universe_expr": users, "universe_text": "Internet users in the past 12 months",
                       "synonyms": ["daily internet use", "heavy internet users", "frequency"], "description": "How often Internet users go online."},
            "ac_strm": act("In the past 3 months, did you watch video content through a streaming service?",
                           ["streaming", "Netflix", "video streaming", "streamers", "watch TV online", "SVOD"],
                           "Watched streamed video such as subscription video services."),
            "ac_pod": act("In the past 3 months, did you listen to podcasts?", ["podcasts", "podcast listeners", "audio shows"],
                          "Listened to podcasts on any device."),
            "ac_mus": act("In the past 3 months, did you listen to music through a streaming service?",
                          ["music streaming", "Spotify", "streaming audio"], "Streamed music."),
            "ac_news": act("In the past 3 months, did you read or watch news online?", ["online news", "news readers", "digital news"],
                           "Consumed news online."),
            "ac_shop": {"topic": "e_commerce", "question_text": "In the past 12 months, did you order goods or services over the Internet?",
                        "universe_expr": users, "universe_text": "Internet users in the past 12 months",
                        "synonyms": ["online shopping", "e-commerce", "online shoppers", "bought online"], "description": "Made any online purchase."},
            "ec_spnd": {"topic": "e_commerce", "question_text": "In total, how much did you spend on goods and services ordered online?",
                        "universe_expr": {"all": [users, {"var": "ac_shop", "eq": 1}]},
                        "universe_text": "Internet users who ordered online", "synonyms": ["online spending", "spend", "big spenders"],
                        "description": "Total annual online spending band."},
            "sm_use": act("In the past 3 months, did you use social networking sites or apps?",
                          ["social media", "Facebook", "Instagram", "TikTok", "social networks"], "Used social media."),
            "dv_smart": {"topic": "devices", "question_text": "Do you have a smartphone for personal use?",
                         "synonyms": ["smartphone", "mobile phone", "cell phone"], "description": "Owns a smartphone."},
        },
        "harmonized": {
            "h_province": {"source": "province", "label": "Province (harmonized)",
                           "map": {str(p[0]): p[1] for p in PROVINCES}, "labels": {p[1]: p[2] for p in PROVINCES},
                           "synonyms": ["province"] + [p[2] for p in PROVINCES] + [p[1] for p in PROVINCES]},
            "h_age_band": {"source": "age_grp", "label": "Age band (harmonized)",
                           "map": {str(i + 1): b for i, b in enumerate(AGE_BANDS)},
                           "labels": {b: AGE_LABELS[i] for i, b in enumerate(AGE_BANDS)},
                           "synonyms": ["age", "young adults", "seniors", "millennials", "youth", "older adults"]},
            "h_gender": {"source": "gender", "label": "Gender (harmonized)", "map": {"1": "M", "2": "W"},
                         "labels": {"M": "Men+", "W": "Women+"}, "synonyms": ["gender", "men", "women"]},
            "h_income_quintile": {"source": "hhincq", "label": "Household income quintile (harmonized)",
                                  "map": {str(i): f"Q{i}" for i in range(1, 6)},
                                  "labels": {f"Q{i}": l for i, l in zip(range(1, 6), ["Lowest quintile", "Second quintile", "Third quintile", "Fourth quintile", "Highest quintile"])},
                                  "synonyms": ["income", "income quintile", "affluent", "high income", "low income"]},
        },
    }
