---
source_id: llvm3_pass_manual
dataset_id: llvm
source_url: https://releases.llvm.org/3.0/docs/Passes.html
source_kind: official_product_documentation
source_status: public_html_checked
---

# LLVM 3.0 pass meanings

LLVM 3.0 distinguishes analysis passes, which compute or report information,
from transformation passes, which can change program IR. Its manual lists
`iv-users` and `print-used-types` as analyses. It lists `gvn` (global value
numbering), `instcombine` (instruction combination), `inline` (function
inlining), `jump-threading`, `simplifycfg` (control-flow simplification),
`sccp` and `ipsccp` (conditional constant propagation), and `licm`
(loop-invariant code motion) as transformations.

These are general pass descriptions, not rules that any pass must be selected
with another or that any selection will improve this benchmark's `PERF-`.
The manual alone does not recover the benchmark's pass order or timed boundary.
