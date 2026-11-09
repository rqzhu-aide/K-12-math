"""Export the public practice app for GitHub Pages using shared Python 3.11+.

Only explicitly selected app files and tracked public database inputs are read.
Question catalogs contain navigation fields; individual questions load on demand.
No model connections, settings, custom banks, source-index bundles or server files
are copied into the website. The derived graph index stays in a temporary folder.
"""
from __future__ import annotations

import argparse
from contextlib import closing
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from urllib.parse import quote


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "math-practice/runtime"))
from question_banks import browser_question, load_question  # noqa: E402
from question_graph import graph_payload  # noqa: E402
import curriculum_graph  # noqa: E402
import knowledge_graph  # noqa: E402


BANKS = {
    "cn-math": {
        "folder": "cn-math-bank", "label": "Chinese curriculum (English)",
        "license": "CC-BY-NC-4.0",
        "sourceURL": "https://github.com/xiaoyang111222/cn-math-taxonomy",
    },
    "amc": {
        "folder": "amc-bank", "label": "AMC contests",
        "attribution": "American Mathematics Competitions, Mathematical Association of America (MAA)",
        "license": "CC-BY-NC-SA-4.0", "sourceURL": "https://maa.org/student-programs/amc/",
    },
}
APP_FILES = (
    "index.html", "answer-check.js", "practice-feedback.js", "curriculum-path.js",
    "graph-evidence.js", "theme.css", "theme.js", "speech-input.js", "speech-worklet.js",
    "hosted-data.js", "site.webmanifest", "images/app-192.png", "images/app-512.png",
)
GRAPH_SOURCE_FILES = (
    "metadata.json", "nodes.json", "relationships.json", "mappings.jsonl",
    "curricula.json", "alignments.json",
)
NAVIGATION_FIELDS = ("id", "level", "year", "grade", "unit", "batch", "topic", "number")
FIGURE = re.compile(r"\[Figure \d+\]\(([^)]+)\)")


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True,
                       separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(json_bytes(value))


def public_inventory(root):
    """Git's tracked inventory prevents ignored local bank/assets from leaking."""
    result = subprocess.run(["git", "ls-files", "--stage", "-z"], cwd=root,
                            capture_output=True, check=True)
    files = set()
    for entry in result.stdout.decode("utf-8").split("\0"):
        if not entry:
            continue
        mode, _, stage_path = entry.split(" ", 2)
        stage, relative = stage_path.split("\t", 1)
        if stage != "0":
            raise ValueError("Resolve the Git conflict before building: " + relative)
        if mode not in ("100644", "100755"):
            raise ValueError("Pages inputs must be ordinary files: " + relative)
        files.add(relative)
    return files


def copy_file(root, output, relative, *, inventory=None):
    if inventory is not None and relative not in inventory:
        raise ValueError("Required public input is not tracked: " + relative)
    source = root / relative
    if source.is_symlink() or not source.resolve().is_relative_to(root):
        raise ValueError("Public input leaves the checkout: " + relative)
    target = output / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)


def copy_public_assets(root, output, inventory):
    for name in APP_FILES:
        # These exact files include the newly authored hosted entry and app icons.
        copy_file(root, output, "math-practice/" + name)
    for relative in sorted(inventory):
        asset = (relative.startswith("math-practice/vendor/")
                 or relative.startswith("math-practice/images/")
                 or any(relative.startswith("database/" + bank["folder"] + "/figures/")
                        for bank in BANKS.values())
                 or relative.startswith("database/amc-bank/official-solutions/"))
        notice = (relative in ("LICENSE", "THIRD_PARTY_NOTICES.md", "README.md",
                               "math-practice/README.md", "database/amc-bank/ADAPTATIONS.md",
                               "database/amc-bank/sources.json")
                  or re.fullmatch(r"database/(amc-bank|cn-math-bank|knowledge-graph)/(LICENSE|NOTICE.md)", relative))
        if asset or notice:
            copy_file(root, output, relative, inventory=inventory)


def hosted_entry(output):
    path = output / "math-practice/index.html"
    html = path.read_text(encoding="utf-8-sig")
    bank_scripts = ('<script src="../database/cn-math-bank/bank.js"></script>\n'
                    '<script src="../database/amc-bank/bank.js"></script>\n'
                    '<script src="../custom-banks/banks.js"></script>')
    if html.count(bank_scripts) != 1:
        raise ValueError("The bank script entry changed; update the Pages export transform.")
    html = html.replace(bank_scripts, '<script src="hosted-config.js"></script>\n'
                                     '<script src="hosted-data.js"></script>')
    head = ('<link rel="manifest" href="site.webmanifest">\n'
            '<link rel="apple-touch-icon" href="images/app-192.png">\n'
            '<link rel="icon" type="image/png" href="images/app-192.png">\n')
    if html.count("</head>") != 1:
        raise ValueError("The app needs a single head element.")
    path.write_text(html.replace("</head>", head + "</head>"), encoding="utf-8", newline="\n")
    config = {
        "catalogs": ["../data/catalogs/" + bank + ".json" for bank in BANKS],
        "browse": {layer: "../data/paths/" + layer + ".json" for layer in curriculum_graph.LAYERS},
    }
    (output / "math-practice/hosted-config.js").write_bytes(
        b"window.MATH_PRACTICE_HOSTED=" + json_bytes(config).rstrip() + b";\n")
    # Relative links work under both a project Pages prefix and a local preview.
    (output / "index.html").write_text(
        '<!doctype html><html lang="en"><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>Math Practice</title><script>'
        'location.replace("math-practice/"+location.search+location.hash);'
        '</script><p><a href="math-practice/">Open Math Practice</a></p></html>\n',
        encoding="utf-8", newline="\n")
    (output / ".nojekyll").write_bytes(b"")
    # The branch artifact contains byte-bound evidence. Preserve those bytes even
    # when a maintainer's shared Git installation enables core.autocrlf.
    (output / ".gitattributes").write_bytes(b"* -text\n")


def publish_evidence(value, bank_root, root, output, inventory, copied):
    """Resolve each displayed evidence pointer from its bank and verify the bytes."""
    if isinstance(value, list):
        for item in value:
            publish_evidence(item, bank_root, root, output, inventory, copied)
    elif isinstance(value, dict):
        relative, expected = value.get("path"), value.get("sha256")
        if isinstance(relative, str) and expected is not None:
            source = (bank_root / relative).resolve()
            evidence_root = root / "database/knowledge-graph/evidence"
            if not source.is_relative_to(evidence_root):
                raise ValueError("Question evidence leaves the public evidence folder: " + relative)
            public_path = source.relative_to(root).as_posix()
            if public_path not in inventory:
                raise ValueError("Question evidence is not tracked: " + public_path)
            if public_path not in copied:
                data = source.read_bytes()
                copied[public_path] = hashlib.sha256(data).hexdigest()
                copy_file(root, output, public_path, inventory=inventory)
            if copied[public_path] != expected:
                raise ValueError("Question evidence hash differs: " + public_path)
            value["path"] = "../" + public_path
        for item in value.values():
            if isinstance(item, (dict, list)):
                publish_evidence(item, bank_root, root, output, inventory, copied)


def export_questions(root, output, inventory, graph_root):
    evidence, counts = {}, {}
    with closing(knowledge_graph._connect_readonly(graph_root / "database/knowledge-graph/knowledge.sqlite3")) as db:
        mappings = {row[0]: json.loads(row[1]) for row in db.execute("SELECT question_id,raw_json FROM questions")}
        version = db.execute("SELECT value FROM metadata WHERE key='graphVersion'").fetchone()[0]
    for bank_id, metadata in BANKS.items():
        source_index = "database/" + metadata["folder"] + "/source-index.json"
        if source_index not in inventory:
            raise ValueError("Required bank source index is not tracked: " + source_index)
        prefix = "database/" + metadata["folder"] + "/questions/"
        paths = sorted(p for p in inventory if p.startswith(prefix) and p.endswith(".json"))
        catalog = {key: value for key, value in metadata.items() if key != "folder"}
        catalog.update(id=bank_id, figuresBase="../database/" + metadata["folder"] + "/figures/", questions=[])
        for relative in paths:
            record = load_question(root / relative, root=root)
            item = browser_question(record, root=root)
            qid = item["id"]
            mapping = mappings.pop(qid)
            if mapping["bank"] != bank_id:
                raise ValueError("Question bank differs from the public graph: " + qid)
            item["knowledgeGraph"] = graph_payload(mapping, version)
            publish_evidence(item, (root / relative).parent.parent, root, output, inventory, evidence)
            body = "\n".join([item["question"], *item.get("choices", {}).values(),
                                *[m.get("explanation", "") for m in item.get("solutionMethods", [])]])
            for figure in FIGURE.findall(body):
                figure_path = (root / relative).parent.parent / figure
                expected = figure_path.resolve().relative_to(root).as_posix()
                if expected not in inventory or not (output / expected).is_file():
                    raise ValueError("A question figure is not published: " + expected)
            write_json(output / "data/questions" / bank_id / (qid + ".json"), item)
            stub = {key: item[key] for key in NAVIGATION_FIELDS if key in item}
            stub["questionURL"] = "../data/questions/" + bank_id + "/" + qid + ".json"
            catalog["questions"].append(stub)
        write_json(output / "data/catalogs" / (bank_id + ".json"), catalog)
        counts[bank_id] = len(catalog["questions"])
        print(f"Exported {bank_id}: {counts[bank_id]} questions", flush=True)
    if mappings:
        raise ValueError("The public graph contains questions outside the published banks.")
    return counts, len(evidence)


def export_curricula(graph_root, output, question_count):
    counts = {}
    for layer in curriculum_graph.LAYERS:
        browse = curriculum_graph.browse_layer(layer, graph_root)
        if layer == "ailleo":
            browse["nodes"] = [{key: n.get(key) for key in ("id", "name", "nameZh", "description", "kind")}
                               for n in browse["nodes"]]
        else:
            browse["nodes"] = [{**{key: n.get(key) for key in ("id", "label", "description", "placement")},
                "placement": {**n.get("placement", {}), **({"category": n["metadata"]["domainName"]}
                    if layer == "US" and n.get("metadata", {}).get("domainName") else {})}}
                for n in browse["nodes"]]
        browse["relationships"] = [{key: edge.get(key) for key in
            ("id", "fromId", "toId", "nodeId", "prerequisiteId", "relation", "directed")}
            for edge in browse["relationships"]]
        browse["alignments"] = [{key: alignment[key] for key in
            ("id", "nodeId", "layer", "sourceNodeId", "relation", "status")}
            for alignment in browse["alignments"]]
        for node in browse["nodes"]:
            filename = quote(node["id"], safe="") + ".json"
            practice = (curriculum_graph.practice_candidates(node["id"], layer, graph_root, limit=question_count)
                        if layer == "ailleo" else curriculum_graph.practice_for_source(
                            node["id"], layer, graph_root, limit=question_count))
            write_json(output / "data/practice" / layer / filename, practice)
            # Percent signs in the filename itself must be encoded in the URL.
            node["practiceURL"] = "../data/practice/" + layer + "/" + quote(filename, safe="")
        write_json(output / "data/paths" / (layer + ".json"), browse)
        counts[layer] = len(browse["nodes"])
        print(f"Exported {layer}: {counts[layer]} concepts or standards", flush=True)
    return counts


def build(output, root=ROOT):
    root, output = root.resolve(), output.resolve()
    if output == root or root.is_relative_to(output) or output.is_relative_to(root):
        raise ValueError("Choose a staging output folder outside the source checkout.")
    if output.exists() and any(output.iterdir()):
        raise ValueError("Choose an empty output folder; the exporter never deletes previous output.")
    inventory = public_inventory(root)
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="math-practice-pages-") as temporary:
        graph_root = Path(temporary)
        source = graph_root / "database/knowledge-graph/source"
        source.mkdir(parents=True)
        # This isolated source folder intentionally has no local mapping overlay.
        for name in GRAPH_SOURCE_FILES:
            relative = "database/knowledge-graph/source/" + name
            if relative not in inventory:
                raise ValueError("Required public graph source is not tracked: " + relative)
            shutil.copyfile(root / relative, source / name)
        print("Validating public question and graph bindings...", flush=True)
        report = knowledge_graph.build_database(root, source_dir=source,
            db_path=graph_root / "database/knowledge-graph/knowledge.sqlite3", check_bindings=True)
        counts, evidence_count = export_questions(root, output, inventory, graph_root)
        curricula = export_curricula(graph_root, output, sum(counts.values()))
    copy_public_assets(root, output, inventory)
    hosted_entry(output)
    info = {"schemaVersion": 1, "kind": "math_practice_public_pages",
            "questions": counts, "curriculumNodes": curricula, "evidenceFiles": evidence_count,
            "graphVersion": report["graphVersion"], "graphSourceDigest": report["sourceDigest"]}
    write_json(output / "build-info.json", info)
    print(json.dumps(info, sort_keys=True), flush=True)
    return info


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True,
                        help="Empty staging directory outside this source checkout")
    args = parser.parse_args()
    build(args.output)
