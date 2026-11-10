"""Command line.

  python -m pumfai setup                 generate synthetic data and ingest it
  python -m pumfai ask "question"        ask (needs ANTHROPIC_API_KEY)
  python -m pumfai tabulate spec.json    run a spec directly (no LLM)
  python -m pumfai search "podcasts"     search the catalog
  python -m pumfai eval                  run the golden set (needs ANTHROPIC_API_KEY)
  python -m pumfai serve                 start the API on :8000
"""
from __future__ import annotations

import argparse
import json
import sys

from . import config


def main(argv=None):
    ap = argparse.ArgumentParser(prog="pumfai")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("setup")
    sub.add_parser("generate-data")
    sub.add_parser("ingest")
    p = sub.add_parser("ask"); p.add_argument("question"); p.add_argument("--choice", action="append", default=[],
                                                                          help="phrase=code, after a clarify")
    p.add_argument("--json", action="store_true")
    p = sub.add_parser("tabulate"); p.add_argument("spec_file")
    p = sub.add_parser("search"); p.add_argument("text")
    p = sub.add_parser("eval"); p.add_argument("--limit", type=int); p.add_argument("--out")
    p = sub.add_parser("serve"); p.add_argument("--port", type=int, default=8000)
    a = ap.parse_args(argv)

    if a.cmd in ("setup", "generate-data"):
        from .synthetic import generate
        print("generated", generate(config.data_dir()))
    if a.cmd in ("setup", "ingest"):
        from .ingest import ingest
        out = ingest(config.raw_dir(), config.data_dir())
        print("ingested", out, json.loads((out / "catalog.json").read_text())["release"]["quality_report"])
    if a.cmd == "search":
        from .catalog import Catalog
        for r in Catalog.load(config.release_dir()).search(a.text):
            print(f"{r['score']:8.2f}  {r['code']:<18} {r['label']}")
    if a.cmd == "tabulate":
        from .engine import Engine
        from .render import markdown
        print(markdown(Engine(config.release_dir()).tabulate(json.loads(open(a.spec_file).read()))))
    if a.cmd == "ask":
        from .engine import Engine
        from .llm import AnthropicLLM
        from .pipeline import Pipeline
        choices = dict(c.split("=", 1) for c in a.choice)
        out = Pipeline(Engine(config.release_dir()), AnthropicLLM(), log_dir=config.log_dir()).ask(a.question, choices)
        if a.json:
            print(json.dumps({k: v for k, v in out.items() if k != "result"}, indent=1, default=str))
        elif out["status"] == "answered":
            print(out["answer"], "\n\n" + out["table_markdown"])
        elif out["status"] == "clarify":
            print(out["message"])
            for c in out["clarify"]:
                print(f"  '{c['phrase']}':", ", ".join(f"{o['code']} ({o['label']})" for o in c["options"]))
            print('Re-run with --choice "phrase=code"')
        else:
            print(out["status"] + ":", out.get("message"), out.get("errors", ""))
    if a.cmd == "eval":
        from .evaluate import run
        run(limit=a.limit, out=a.out)
    if a.cmd == "serve":
        import uvicorn
        uvicorn.run("pumfai.api:app", port=a.port)


if __name__ == "__main__":
    sys.exit(main())
