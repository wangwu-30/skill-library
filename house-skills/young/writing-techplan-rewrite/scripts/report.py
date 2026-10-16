#!/usr/bin/env python3
"""Advisory report for writing-techplan-rewrite output. Never a gate: always exits 0."""
import argparse, json, re
SECTIONS = {"结论": r"结论", "需要拍板": r"拍板", "背景与目标": r"背景", "方案": r"方案", "备选方案": r"备选",
            "风险": r"风险", "最大风险标注": r"最大风险", "上线与回滚": r"回滚", "非目标": r"非目标"}
BLOG = {"第一人称叙事": r"(?:^|[。！？\n])\s*我(?!们将)", "设问": r"[吗呢]？|？\s*(?:答案|其实)", "感叹": r"！",
        "口号句式": r"不是[^。\n]{1,20}而是|不只是|不仅仅是", "寒暄": r"大家好|各位|希望对你|欢迎"}
TERM = re.compile(r"[A-Za-z][A-Za-z0-9_\-]*[A-Za-z0-9]|[A-Z]{2,}")
def glossary_terms(p):
    if not p: return set()
    t = set()
    for line in open(p, encoding="utf-8"):
        m = re.match(r"\s*[-*|]?\s*\**([^:：|*]+?)\**\s*[:：|]", line)
        if m: t.add(m.group(1).strip().lower())
    return t
def main():
    a = argparse.ArgumentParser(); a.add_argument("doc"); a.add_argument("--glossary"); a.add_argument("--json", action="store_true")
    o = a.parse_args(); s = open(o.doc, encoding="utf-8").read()
    body = re.split(r"\n#+\s*附录", s)[0]
    prop = re.split(r"\n#+\s*术语提案", s); proposed = prop[1].lower() if len(prop) > 1 else ""
    g = glossary_terms(o.glossary)
    first = next((l for l in s.splitlines() if l.strip() and not l.startswith("#")), "")
    terms = sorted({t for t in TERM.findall(body)})
    off = [t for t in terms if t.lower() not in g and t.lower() not in proposed]
    r = {"sections_present": {k: bool(re.search(v, s)) for k, v in SECTIONS.items()},
         "conclusion_near_top": bool(re.search(r"结论", "\n".join(s.splitlines()[:8]))),
         "body_chars": len(re.sub(r"\s", "", body)), "terms_in_body": len(terms),
         "terms_in_glossary": sum(t.lower() in g for t in terms), "terms_proposed": sum(t.lower() in proposed for t in terms),
         "terms_off_glossary_unproposed": off,
         "blog_markers": {k: len(re.findall(v, body, re.M)) for k, v in BLOG.items()},
         "advisory_only": True}
    print(json.dumps(r, ensure_ascii=False, indent=1))
if __name__ == "__main__": main()
