"""Mutation analysis of the c2 oracles (looktwin thread 102395). Mutate each reference solution ref/T*.py one token
at a time (comparison and arithmetic operators, boolean ops, integer literals +-1, one character deleted from a regex
or string literal, a call dropped), then ask two oracles which mutants they kill:
  H = the 24 pre-registered hidden tests (hidden_tests.py, unchanged);
  P = property/metamorphic checks written by me from tasks.json only (props.py), seeded random inputs.
A P-kill counts only on inputs where the reference itself passes the same property (the reference has known spec
defects, T2 and T3, so P failing there must not count as a kill). Output: mutants.jsonl + a summary."""
import ast, io, json, os, re, subprocess, sys, tokenize, hashlib
HERE = os.path.dirname(os.path.abspath(__file__)); C2 = os.path.join(HERE, "trial", "c2")
FUNC = {"T1": "split_amount", "T2": "parse_retry_after", "T3": "mask_secrets", "T4": "dedupe_events", "T5": "safe_join"}
SWAP = {"<": ["<=", ">"], "<=": ["<", ">="], ">": [">=", "<"], ">=": [">", "<="], "==": ["!="], "!=": ["=="],
        "+": ["-"], "-": ["+"], "*": ["/"], "//": ["/"], "%": ["//"], "and": ["or"], "or": ["and"],
        "not": [""], "in": ["not in"], "max": ["min"], "min": ["max"]}


def line_mutants(src):
    """statement deletion (line -> pass), if-condition forced True/False, a one-argument call replaced by its argument"""
    L = src.splitlines(keepends=True)
    for i, l in enumerate(L):
        st = l.strip(); ind = l[:len(l) - len(l.lstrip())]
        if not ind or not st or st.startswith(("def ", "#")): continue
        yield f"stmtdel@{i + 1}", "".join(L[:i] + [ind + "pass\n"] + L[i + 1:])
        m = re.match(r"(\s*if )(.*?)(:.*)$", l, re.S)
        if m:
            for c in ("True", "False"): yield f"if{c}@{i + 1}", "".join(L[:i] + [m.group(1) + c + m.group(3)] + L[i + 1:])
    for m in re.finditer(r"\b(?:[\w.]+\.)?(normpath|abspath|strip|lstrip|float|int|to_integral_value)\(", src):
        a = m.start(); depth = 0; j = m.end() - 1
        for j in range(m.end() - 1, len(src)):
            depth += src[j] == "("; depth -= src[j] == ")"
            if depth == 0: break
        inner = src[m.end():j]
        if m.group(0).startswith(".") or src[a - 1] == ".":
            continue
        if "," not in inner and inner: yield f"calldrop:{m.group(1)}@{a}", src[:a] + "(" + inner + ")" + src[j + 1:]
    for m in re.finditer(r"\.(strip|lstrip|to_integral_value)\(([^()]*)\)", src):
        yield f"methoddrop:{m.group(1)}@{m.start()}", src[:m.start()] + src[m.end():]


def mutants(src):
    yield from line_mutants(src)
    toks = list(tokenize.generate_tokens(io.StringIO(src).readline))
    lines = src.splitlines(keepends=True)
    off = [0]
    for l in lines: off.append(off[-1] + len(l))
    pos = lambda rc: off[rc[0] - 1] + rc[1]
    for t in toks:
        a, b = pos(t.start), pos(t.end)
        if t.string in SWAP:
            for r in SWAP[t.string]: yield f"{t.string}->{r or 'del'}@{t.start}", src[:a] + r + src[b:]
        elif t.type == tokenize.NUMBER and re.fullmatch(r"\d+", t.string):
            n = int(t.string)
            for r in {n + 1, max(0, n - 1)} - {n}: yield f"{n}->{r}@{t.start}", src[:a] + str(r) + src[b:]
        elif t.type == tokenize.STRING:
            q = re.match(r"[rRbBuU]*('''|\"\"\"|'|\")", t.string); h = len(q.group(0)); body = t.string[h:-len(q.group(1))]
            for i in range(len(body)):
                s2 = t.string[:h] + body[:i] + body[i + 1:] + t.string[-len(q.group(1)):]
                yield f"strdel{i}:{body[i]!r}@{t.start}", src[:a] + s2 + src[b:]


def run_hidden(tid, path):
    r = subprocess.run([sys.executable, os.path.join(C2, "hidden_tests.py"), tid, path, FUNC[tid]],
                       capture_output=True, text=True, timeout=60)
    try: res = json.loads(r.stdout.strip().splitlines()[-1])
    except Exception: return None
    return sum(v != "pass" for v in res.values())


def run_props(tid, path):
    r = subprocess.run([sys.executable, os.path.join(HERE, "props.py"), tid, path, FUNC[tid]],
                       capture_output=True, text=True, timeout=120)
    try: return json.loads(r.stdout.strip().splitlines()[-1])
    except Exception: return None


if __name__ == "__main__":
    os.makedirs(os.path.join(HERE, "mut"), exist_ok=True)
    out = open(os.path.join(HERE, "mutants.jsonl"), "w")
    for tid in FUNC:
        ref = open(os.path.join(C2, "ref", tid + ".py")).read()
        refp = run_props(tid, os.path.join(C2, "ref", tid + ".py"))     # per-input pass vector of the reference
        seen = set()
        for name, src in mutants(ref):
            try: ast.parse(src)
            except SyntaxError: continue
            h = hashlib.sha256(src.encode()).hexdigest()[:12]
            if h in seen or src == ref: continue
            seen.add(h)
            p = os.path.join(HERE, "mut", f"{tid}_{h}.py"); open(p, "w").write(src)
            try: hk = run_hidden(tid, p)
            except subprocess.TimeoutExpired: hk = "timeout"
            try: pv = run_props(tid, p)
            except subprocess.TimeoutExpired: pv = "timeout"
            if isinstance(pv, dict):
                pk = sum(1 for k, ok in pv.items() if refp.get(k) is True and ok is not True)
            else: pk = pv
            row = {"task": tid, "mutant": name, "sha": h, "hidden_fail": hk, "prop_kills": pk}
            out.write(json.dumps(row) + "\n"); out.flush()
