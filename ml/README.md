# SmartShield ML research workspace

This directory contains the evidence-first ML research pipeline. The current
checkpoint completed repository inventory and four-rule feasibility assessment.
No model is trained, loaded, or enabled.

The acceptance corpus is explicitly excluded from ML evaluation. Unknown,
unsupported, compilation-failed, and unreviewed candidates are never converted
to negative labels. See [the feasibility report](results/dataset_feasibility_report.md),
[the annotation guide](docs/ANNOTATION_GUIDE.md), and
[the progress record](docs/PROGRESS.md).

Directories for features, models, training, evaluation, tests, notebooks, and
configuration remain reserved for later phases. They must receive real,
versioned implementations rather than placeholders before being described as
complete.
