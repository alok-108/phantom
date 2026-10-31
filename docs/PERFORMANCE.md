# Lexer/parser performance

Reproducible benchmark: `python scripts/benchmark_lexer_parser.py`
(`--quick` runs only the first two cases). Inputs are generated in memory;
no files are written. Times are single-run measurements on this machine
(Linux VM, Python 3.12), so compare runs on the same machine, not across
machines. No tracemalloc is used: it slows the parser several-fold and
would dominate the numbers.

## Results (2026-11-01)

| Case | Bytes | Lines | Instructions | Seconds |
| :--- | ---: | ---: | ---: | ---: |
| plain_50k_lines | 777780 | 50000 | 0 | 0.21 |
| comment_10k_instructions | 438890 | 10000 | 10000 | 0.17 |
| long_line_1mb | 1000010 | 1 | 0 | 0.08 |
| ws_payload_100kb | 900317 | 100035 | 1 | 0.43 |
| mixed_10k_functions | 736670 | 30000 | 10000 | 0.27 |

Scaling check for plain source: 10k lines 0.04s, 50k lines 0.20s,
100k lines 0.42s — linear, no quadratic behaviour and no pathological
case was found in these cases, so no optimisation is proposed here
(issue #35 asked to measure first, and only then optimise on a real
problem).
