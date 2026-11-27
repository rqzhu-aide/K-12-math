"""Render the repository and website directories from the same source inventory."""
import argparse
from datetime import date
from html import escape
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATABASE = ROOT / "database"
WEB = "https://math-practice.ailleo.net/dataset-acknowledgements.html"
DIRECTORY_PATH = "database/question-bank-directory.json"


def english(value):
    return value if isinstance(value, str) else value[0]


def bilingual(value):
    if isinstance(value, str):
        return escape(value)
    en, zh = value
    return (f'<span class="copy-en">{escape(en)}</span>'
            f'<span class="copy-cn" lang="zh-CN">{escape(zh)}</span>')


def item_size(row):
    return f'{row["size"]:,}' if isinstance(row["size"], int) else row["size"]


def table(rows, released, html):
    size_label = ["Questions", "题数"] if released else ["Source size", "来源规模"]
    labels = [["Source", "来源"], size_label, ["Approximate coverage", "大致范围"], ["Source terms", "原始资料许可"]]
    if html:
        heading = "collection-links" if released else "candidate-sources"
        lines = [f'<table class="bank-table" aria-labelledby="{heading}" role="table">',
                 '  <thead role="rowgroup"><tr role="row">',
                 *[f'    <th scope="col" role="columnheader">{bilingual(label)}</th>' for label in labels],
                 '  </tr></thead>', '  <tbody role="rowgroup">']
        for row in rows:
            url = "#" + row["id"] if released else row["url"]
            lines += ['    <tr role="row">',
                      f'      <th scope="row" role="rowheader"><a href="{escape(url)}">{bilingual(row["name"])}</a></th>']
            for label, value in zip(labels[1:], (item_size(row), row["coverage"], row["terms"])):
                lines.append('      <td role="cell">'
                             f'<span class="cell-label" aria-hidden="true">{bilingual(label)}</span>'
                             f'<span>{bilingual(value)}</span></td>')
            lines.append('    </tr>')
        return "\n".join([*lines, "  </tbody>", "</table>"])
    lines = ["| " + " | ".join(map(english, labels)) + " |", "|---|---:|---|---|"]
    for row in rows:
        name = f'[{english(row["name"])}]({row["url"]})'
        terms = english(row["terms"])
        if released:
            terms = f'[{terms}]({WEB}#{row["id"]})'
        lines.append(f'| {name} | {english(item_size(row))} | {english(row["coverage"])} | {terms} |')
    return "\n".join(lines)


def replace_block(text, key, rendered):
    start, end = f"<!-- directory:{key} -->", f"<!-- /directory:{key} -->"
    if text.count(start) != 1 or text.count(end) != 1:
        raise ValueError(f"Missing or duplicate directory markers for {key}")
    before, body = text.split(start)
    _, after = body.split(end)
    return before + start + "\n" + rendered + "\n" + end + after


def write(path, value, check):
    if path.is_file() and path.read_text(encoding="utf-8") == value:
        return
    if check:
        raise SystemExit(f"Directory needs regeneration: {path}")
    path.write_text(value, encoding="utf-8", newline="\n")


def validate_release_directory(catalog, version, published_counts=None):
    if catalog["version"] != version:
        raise ValueError("The catalog version differs from the question bank version.")
    released = catalog["released"]
    counts = {row["id"]: row["size"] for row in released}
    if len(counts) != len(released) or not all(type(n) is int and n > 0 for n in counts.values()):
        raise ValueError("Released sources must have unique IDs and positive integer counts.")
    if published_counts is not None and counts != published_counts:
        differences = [f"{bank}: directory={counts.get(bank)}, Pages={published_counts.get(bank)}"
                       for bank in sorted(counts.keys() | published_counts.keys())
                       if counts.get(bank) != published_counts.get(bank)]
        raise ValueError("Published question counts differ from the directory. " + ", ".join(differences))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--build-info", type=Path, help="Verify each released count against a Pages build-info.json")
    parser.add_argument("--page", type=Path, help="Update or check the bilingual HTML in a separate site checkout")
    args = parser.parse_args()
    catalog = json.loads((ROOT / DIRECTORY_PATH).read_text(encoding="utf-8"))
    released, candidates = catalog["released"], catalog["candidates"]
    version = (DATABASE / "QUESTION_BANK_VERSION").read_text(encoding="ascii").strip()
    published_counts = None
    if args.build_info:
        build = json.loads(args.build_info.read_text(encoding="utf-8"))
        if build["questionBankVersion"] != version:
            raise ValueError("The Pages build version differs from the question bank version.")
        published_counts = {**build["questions"], **build["practicePools"]}
    validate_release_directory(catalog, version, published_counts)
    total = sum(row["size"] for row in released)
    intro = f"Ailleo Question Bank {version} contains {total:,} questions from {len(released)} sources."
    chinese_intro = f"Ailleo 题库 {version} 共收录 {len(released)} 个来源的 {total:,} 道题。"
    reviewed = date.fromisoformat(catalog["reviewed"])
    scope = "Grade ranges and counts describe the questions included in this release."
    rights = ("Source terms cover the original materials. Individual credits identify worked solutions, "
              "figures and adaptations. CC BY requires attribution, NC limits use to noncommercial purposes, "
              "and SA requires shared adaptations to carry the same or a compatible license.")
    candidate_note = (f"Source sizes as of {reviewed:%B %d, %Y}. These collections are under review "
                      "for a future release. Each size uses the unit shown.")
    md = (f"# Ailleo question bank directory\n\n{intro} {scope} "
          f"[Practice online](https://math-practice.ailleo.net/) · [Bilingual directory and credits]({WEB})\n\n"
          f"## Available in Ailleo\n\n{table(released, True, False)}\n\n{rights}\n\n"
          f"## Sources under review\n\n{candidate_note}\n\n{table(candidates, False, False)}\n\n"
          "## Updating the directory\n\n"
          "For each new collection, record the included question count, coverage and original license in "
          "[the source inventory](question-bank-directory.json). Link the questions and their worked methods "
          "to the skills they assess or use. Regenerate the directory with "
          "`python scripts/render_question_directory.py` and compare it with the release using "
          "`python scripts/render_question_directory.py --check --build-info PATH/TO/build-info.json`.\n")
    write(DATABASE / "QUESTION_BANKS.md", md, args.check)
    # The downloadable desktop edition has its own source layout. Its README links to the online directory.
    page = args.page or ROOT / "math-practice" / "dataset-acknowledgements.html"
    if args.page or page.exists():
        text = page.read_text(encoding="utf-8")
        release_zip = f"https://github.com/rqzhu-aide/K-12-math/releases/download/ailleo-question-bank-v{version}/ailleo-question-bank-{version}.zip"
        for key, value in (
            ("intro", bilingual([intro, chinese_intro]) + "\n" +
             f'<a href="{release_zip}">{bilingual(["Download the full question bank (ZIP)", "下载完整题库（ZIP）"])}</a>'),
            ("size-scope", bilingual([scope, "年级范围和题数仅指本版实际收录的题目。"])),
            ("released", table(released, True, True)),
            ("rights", bilingual([rights, "原始资料适用表中所列许可。各来源的致谢中另有解答、插图和改编资料的署名说明。CC BY 要求署名，NC 限于非商业用途，SA 要求共享改编作品时采用相同或兼容的许可。"])),
            ("candidate-intro", bilingual([candidate_note, f"来源规模核对日期为 {reviewed.year} 年 {reviewed.month} 月 {reviewed.day} 日。以下来源正在评估，供后续版本考虑。各项数量按表中所列单位统计。"])),
            ("candidates", table(candidates, False, True)),
        ):
            text = replace_block(text, key, value)
        write(page, text, args.check)


if __name__ == "__main__":
    main()
