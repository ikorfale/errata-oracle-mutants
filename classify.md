# The 27 mutants the hidden tests miss, classified by hand (second-model review applied)

| class | n | mutants (mutants.jsonl `mutant` field) | why |
|---|---|---|---|
| equivalent | 4 | T1 `methoddrop:to_integral_value`; T2 `stmtdel@8`, `ifFalse@8`; T5 `calldrop:normpath` | Decimal*100 is exact for 2-decimal totals; `parsedate_to_datetime` never returns None (it raises, caught); `abspath` already normalises |
| ambiguous | 8 | T2 `calldrop:int` (inf vs OverflowError above 1e308); T2 `methoddrop:lstrip`, `strdel0:'-'` (`"--5"`: ref raises ValueError, mutant 0.0); T3 `strdel28` (`'{"token": "abc'`: ref leaks, mutant masks); T3 lookbehind `[\w"]`->`[\w]` (differs only on `key: value` inside a quoted string); T5 `calldrop:abspath` (relative base); T5 `stmtdel@4`, `ifFalse@4` (isabs check removed, see note) | mutant differs from ref only where the ref itself is wrong or the spec is silent |
| real, caught by my properties | 6 | T1 `n<=1`, `n<2` (raises on n=1; no hidden test uses n=1); T3 four mutants of the JSON replacement `\1***\3` (hidden D3.3 checks only that the secret is gone and `"n": 1` remains) | |
| real, caught by neither | 9 | T2 `calldrop:float` (returns int); T2 `methoddrop:strip` (`" 120 "` -> 0.0); T3 `\s*`->`\s` (`{"token":"abc123"}` leaks); T3 `\s*`->`s*` JSON (`{"token" : "x"}` leaks); T3 leading `"` dropped (`{"mytoken": "x"}` over-masked); T3 three lookbehind mutants (`mytoken=abc123` over-masked); T3 `\s*`->`s*` key=value (`token = abc123` leaks) | |

Note: the two T5 mutants that delete the `isabs` check are spec-conformant (tasks.json: raise only if the result escapes base; `/srv/files/a` given as an absolute path does not), so they count as ambiguous. Total: 4 + 8 + 6 + 9 = 27. My property that kills them is stricter than the spec.

Distinct behaviours rather than mutants: the 9 caught by neither are 7 behaviours (the three lookbehind mutants are one).

## Reference defects outside the hidden tests (reproduced on clone 1d316fb)

| input | ref | gen |
|---|---|---|
| `safe_join("/", "a")` | ValueError (base `/` rejects every path) | `/a` |
| `parse_retry_after("Wed, 21 Oct 2026 07:28:00 -0000", NOW)` | TypeError (naive datetime minus aware) | 0.0 |
| `parse_retry_after("--5", NOW)` | ValueError | 0.0 |
| `mask_secrets('{"token": "abc')` | unchanged (leaks) | `{"token": ***` |

The last three were found by the second model reading the code, not by my properties.
