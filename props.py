"""Spec-only property checks for c2 (written from tasks.json; I did not use hidden_tests.py or the review to write
them). Seeded inputs, so keys line up across implementations. Prints {"prop#i": true|false|"EXC ..."}.
Usage: python3 props.py TASK path func"""
import sys, json, random, re, string, datetime, email.utils, posixpath, copy, importlib.util
tid, path, func = sys.argv[1:4]
spec = importlib.util.spec_from_file_location("m", path); m = importlib.util.module_from_spec(spec)
R = random.Random(2510); out = {}
try: spec.loader.exec_module(m); f = getattr(m, func)
except Exception as e: print(json.dumps({"LOAD": f"EXC {e}"[:80]})); sys.exit()
def chk(key, fn):
    try: out[key] = bool(fn())
    except Exception as e: out[key] = f"EXC {type(e).__name__}"
def raises(fn):
    try: fn()
    except ValueError: return True
    except Exception: return False
    return False
N = 150
if tid == "T1":
    for i in range(N):
        cents = R.randrange(10 ** R.randint(1, 20)); n = R.randint(1, 12); tot = f"{cents // 100}.{cents % 100:02d}"
        def p(tot=tot, n=n, cents=cents):
            r = f(tot, n); c = [int(x.replace(".", "")) for x in r]
            return (len(r) == n and all(re.fullmatch(r"\d+\.\d\d", x) for x in r) and sum(c) == cents
                    and max(c) - min(c) <= 1 and c == sorted(c, reverse=True))
        chk(f"split#{i}", p)
    for i, n in enumerate((0, -1, -7)): chk(f"n_raises#{i}", lambda n=n: raises(lambda: f("5.00", n)))
    for i in range(10):
        c = R.randrange(1, 10 ** 6); chk(f"neg_raises#{i}", lambda c=c: raises(lambda: f(f"-{c // 100}.{c % 100:02d}", 3)))
elif tid == "T2":
    NOW = datetime.datetime(2026, 10, 22, 12, 0, 0, tzinfo=datetime.timezone.utc)
    for i in range(N):
        d = R.randrange(10 ** R.randint(1, 12)); chk(f"delta#{i}", lambda d=d: f(str(d), NOW) == float(d))
        chk(f"negdelta#{i}", lambda d=d: f(f"-{d + 1}", NOW) == 0.0)
        s = R.randint(-10 ** 6, 10 ** 6); v = email.utils.format_datetime(NOW + datetime.timedelta(seconds=s), usegmt=True)
        chk(f"date#{i}", lambda v=v, s=s: f(v, NOW) == max(0.0, float(s)))
        g = "".join(R.choice(string.ascii_letters + " ,;") for _ in range(R.randint(0, 12)))
        chk(f"garbage#{i}", lambda g=g: f(g, NOW) == 0.0)
elif tid == "T3":
    KEYS = ["password", "token", "api_key", "secret"]; W = ["user=bob", "ok=1", "tokens_used=42", "msg", "failed", "auth", "n=3", "secretary=ann"]
    PUN = [")", "]", "}", ";", ",", ".", "'", "\"", "|", ""]
    for i in range(N):
        k = "".join(c.upper() if R.random() < .3 else c for c in R.choice(KEYS))
        v = "".join(R.choice(string.ascii_letters + string.digits + "_-") for _ in range(R.randint(6, 12)))
        sep = R.choice(["=", ": ", "=", ":"]); pre = " ".join(R.sample(W, R.randint(0, 3))); suf = R.choice(PUN)
        tail = " ".join(R.sample(W, R.randint(0, 2)))
        if R.random() < .3: line = f'{pre} {{"{k}": "{v}", "n": 1}} {tail}'.strip()
        else: line = f"{pre} ({k}{sep}{v}{suf} {tail}".strip() if suf else f"{pre} {k}{sep}{v} {tail}".strip()
        chk(f"exact#{i}", lambda line=line, v=v: f(line) == line.replace(v, "***"))
        chk(f"gone#{i}", lambda line=line, v=v: v not in f(line))
        plain = " ".join(R.sample(W, R.randint(1, 4))); chk(f"untouched#{i}", lambda plain=plain: f(plain) == plain)
elif tid == "T4":
    for i in range(N):
        ev = [{"id": R.choice("abcde"), "ts": R.randint(0, 6), "payload": j} for j in range(R.randint(0, 9))]
        best = {}
        for e in ev:
            if e["id"] not in best or e["ts"] > best[e["id"]]["ts"]: best[e["id"]] = e
        want = sorted((e["id"], e["ts"], e["payload"]) for e in best.values())
        def p(ev=ev, want=want):
            snap = copy.deepcopy(ev); r = f(ev)
            return (ev == snap and sorted((e["id"], e["ts"], e["payload"]) for e in r) == want
                    and [e["ts"] for e in r] == sorted(e["ts"] for e in r))
        chk(f"dedupe#{i}", p)
elif tid == "T5":
    SEG = ["a", "b", "..", ".", "files2", "x.txt", ""]
    for i in range(N):
        base = R.choice(["/srv/files", "/srv/files/", "/srv/./files", "/srv/x/../files", "/", "/srv"])
        up = "/".join(R.choice(SEG) for _ in range(R.randint(1, 4))); up = ("/" + up) if R.random() < .1 else up
        b = posixpath.normpath(base); r = posixpath.normpath(posixpath.join(b, up))
        bad = posixpath.isabs(up) or posixpath.commonpath([b, r]) != b
        chk(f"join#{i}", (lambda base=base, up=up: raises(lambda: f(base, up))) if bad else (lambda base=base, up=up, r=r: f(base, up) == r))
print(json.dumps(out))
