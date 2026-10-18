---
source_id: health_paper
dataset_id: health_closed_issues
source_url: https://arxiv.org/pdf/2301.06577
source_kind: author_research_paper
source_status: public_pdf_checked
---

# Original project-health landscape study

Lustosa and Menzies study prediction of future activity in open-source
projects with little training data. Their random-forest search space includes
the number of trees, minimum samples per leaf, minimum impurity decrease,
maximum depth, and the criterion used to evaluate splits. The paper defines
MRE as absolute prediction error divided by the actual value and Pred40 as
the fraction of predictions with MRE no greater than 40 percent. It also
studies standardized accuracy (SA). These definitions explain the research
setting but do **not** prove that the benchmark CSV's `ACC+` is identical to SA
or that the CSV's `criterion` codes directly match the paper's named choices.
