# No deployed model

The integration gate failed. This directory deliberately contains no trained
predictor, pickle/joblib file or production model metadata. `results/metrics.json`
records the historical pilot's configuration, coefficient interpretation and
in-memory serialized size. `src/inference.py` is research-only shared scoring
code; the API does not import it. Reproduce training from pinned sources and
reviewed labels rather than loading untrusted serialized models.
