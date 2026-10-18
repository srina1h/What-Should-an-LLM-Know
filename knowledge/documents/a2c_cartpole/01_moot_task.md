---
source_id: moot_rl_readme
dataset_id: a2c_cartpole
source_path: third_party/moot/optimize/rl/README.md
source_url: https://github.com/timm/moot/blob/main/optimize/rl/README.md
source_kind: repository_documentation
source_status: locally_available
---

# MOOT A2C CartPole task

MOOT describes tuning A2C training for the CartPole environment. The frozen
CSV has seven hyperparameter inputs: `Learning_rate`, `Gamma`, `Nsteps`,
`Entcoef`, `Vfcoef`, `Gradnorm`, and `Lambda`. The benchmark headers request
higher `EvalMeanReturn+` and `Score+`, and lower `EvalVarReturn-` and
`ConvergenceTime-`. MOOT calls these mean evaluation return, evaluation
return variance, convergence time, and an overall performance score.

The README does not provide the formula for `Score+`, a convergence test or
time unit for `ConvergenceTime-`, or an encoding rule for the numeric
`Learning_rate` column. Do not assume a raw learning rate or a base-10
exponent from this source.
