"""Turn an engine result into display values. The narrator and the number checker both
use these rounded values, so what the narrator may say is exactly what the user sees."""
from __future__ import annotations


def pct(v):
    return None if v is None else round(v, 1)


def count(v):
    return None if v is None else int(round(v, -3))


def idx(v):
    return None if v is None else int(round(v))


def display_table(result: dict) -> list[dict]:
    """Flat list of display cells: one per (row variable, value, column)."""
    out = []
    for block in result["rows"]:
        for val in block["values"]:
            for col in result["columns"]:
                c = val["cells"][col["code"]]
                out.append({
                    "row_var": block["label"], "row_value": val["label"], "column": col["label"],
                    "flag": c["flag"], "pct": pct(c["col_pct"]), "count": count(c["weighted_count"]),
                    "index": idx(c["index"]) if col["code"] != "total" else None,
                    "n": c["unweighted_n"],
                })
    return out


def markdown(result: dict, catalog=None) -> str:
    lines = []
    head = [col["label"] for col in result["columns"]]
    for block in result["rows"]:
        lines.append(f"**{block['label']}** (base: {block['universe']}; unweighted n = {block['base_unweighted_n']:,}; "
                     f"weighted = {count(block['base_weighted']):,})")
        lines.append("")
        lines.append("| " + " | ".join(["Response"] + head) + " |")
        lines.append("| " + " | ".join(["---"] + ["--:"] * len(head)) + " |")
        for val in block["values"]:
            cells = []
            for col in result["columns"]:
                c = val["cells"][col["code"]]
                if c["flag"] == "F":
                    cells.append("F")
                    continue
                s = f"{pct(c['col_pct']):.1f}%"
                if col["code"] != "total" and c["index"] is not None:
                    s += f" ({idx(c['index'])})"
                if c["flag"] == "E":
                    s += " E"
                cells.append(s)
            lines.append("| " + " | ".join([val["label"]] + cells) + " |")
        lines.append("")
    lines.append("Column percentages; index vs Total in brackets (100 = same as total). "
                 "E = use with caution (high sampling variability). F = too unreliable to be published.")
    return "\n".join(lines)


def narrator_facts(result: dict) -> str:
    """Compact text the narrator receives: only displayable numbers, flags spelled out."""
    lines = [f"Data: {result['title']} (release {result['release_id']})."]
    for block in result["rows"]:
        lines.append(f"\nVariable: {block['label']}. Base: {block['universe']}; "
                     f"weighted population {count(block['base_weighted']):,}.")
        for val in block["values"]:
            for col in result["columns"]:
                c = val["cells"][col["code"]]
                where = "all in base" if col["code"] == "total" else col["label"]
                if c["flag"] == "F":
                    lines.append(f"- {val['label']} / {where}: SUPPRESSED (too unreliable; do not estimate)")
                    continue
                txt = f"- {val['label']} / {where}: {pct(c['col_pct']):.1f}% ({count(c['weighted_count']):,} people)"
                if col["code"] != "total" and c["index"] is not None:
                    txt += f", index {idx(c['index'])}"
                if c["flag"] == "E":
                    txt += " [USE WITH CAUTION]"
                lines.append(txt)
    return "\n".join(lines)
