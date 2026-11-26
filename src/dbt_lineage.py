"""Generate docs/DBT_LINEAGE.md (a Mermaid diagram that GitHub renders) from the real dbt manifest.
Run after `dbt build`/`dbt docs generate`. If the manifest does not exist yet the script says so and exits cleanly."""
import json
from src.config import ROOT, DOCS_DIR

LAYERS = [("sources", "Raw sources (DuckDB schema raw)"), ("staging", "Staging (views)"), ("intermediate", "Intermediate (tables)"),
          ("marts", "Marts: star schema (tables)"), ("analysis", "Analysis answers (tables)"), ("seeds", "Seeds (assumptions)")]


def main():
    mf = ROOT / "dbt_project" / "target" / "manifest.json"
    if not mf.exists():
        print("no dbt manifest yet: run `cd dbt_project && dbt build --profiles-dir .` first")
        return
    m = json.loads(mf.read_text(encoding="utf-8"))
    nodes = {k: v for k, v in {**m["nodes"], **m["sources"]}.items() if v["resource_type"] in ("model", "seed", "source")}
    def layer(n):
        if n["resource_type"] == "source": return "sources"
        if n["resource_type"] == "seed": return "seeds"
        return n["path"].replace("\\", "/").split("/")[0]
    ident = lambda k: k.replace(".", "_").replace("-", "_")
    L = ["# dbt lineage (generated)", "", "Generated from `dbt_project/target/manifest.json` by `python -m src.dbt_lineage`. Arrows point from an input to the model that uses it.", "",
         "```mermaid", "flowchart LR"]
    for key, title in LAYERS:
        members = [k for k, n in nodes.items() if layer(n) == key]
        if not members: continue
        L.append(f'  subgraph {key}["{title}"]')
        L += [f'    {ident(k)}["{nodes[k]["name"]}"]' for k in sorted(members, key=lambda x: nodes[x]["name"])]
        L.append("  end")
    edges = 0
    for k, n in nodes.items():
        if n["resource_type"] != "model":
            continue
        for dep in n["depends_on"]["nodes"]:
            if dep in nodes:
                L.append(f"  {ident(dep)} --> {ident(k)}"); edges += 1
    L += ["```", "", f"{sum(1 for n in nodes.values() if n['resource_type'] == 'model')} models, {sum(1 for n in nodes.values() if n['resource_type'] == 'seed')} seeds, "
          f"{sum(1 for n in nodes.values() if n['resource_type'] == 'source')} sources, {edges} dependencies. "
          "Tests (44) are defined in `models/*/schema.yml` and `dbt_project/tests/`."]
    (DOCS_DIR / "DBT_LINEAGE.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"wrote docs/DBT_LINEAGE.md ({edges} edges)")


if __name__ == "__main__":
    main()
