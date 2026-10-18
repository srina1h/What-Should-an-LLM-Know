---
source_id: sb3_a2c_v2_4_0
dataset_id: a2c_cartpole
source_url: https://stable-baselines3.readthedocs.io/en/v2.4.0/modules/a2c.html
source_kind: official_library_documentation
source_status: public_html_checked
---

# A2C parameter meanings

Stable-Baselines3 version 2.4.0 documents `learning_rate` as the update
learning rate, `gamma` as the discount factor, and `n_steps` as environment
steps collected per update. It documents `ent_coef` as the entropy-loss
weight, `vf_coef` as the value-function-loss weight, `max_grad_norm` as the
gradient-clipping threshold, and `gae_lambda` as a generalized-advantage
estimation bias-variance setting. These correspond by name to the seven
benchmark inputs, including `Lambda` for `gae_lambda`.

This reference explains A2C terminology; it does not establish that MOOT's
CSV was generated with Stable-Baselines3 2.4.0, that its numeric fields use
the library's raw parameter scales, or that any setting must improve CartPole
returns. The benchmark's learning-rate encoding and outcome formulas remain
unverified.
