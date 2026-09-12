# Bounded Qdrant performance guidance

Inspect installed Qdrant version and local/server/cloud mode before applying
memory or search advice. Measure actual collection/search behavior and local
file-lock constraints. Do not import cluster, Kubernetes, multitenancy, or
deployment guidance into this single-project performance boundary.
