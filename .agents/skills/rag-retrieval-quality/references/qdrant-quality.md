# Bounded Qdrant guidance

Consult the pinned Qdrant reference for exact-vs-ANN diagnosis, collection and
vector compatibility, filters, and hybrid-search concepts. The project uses
Python-side BM25/dense/lexical collection and RRF; do not replace it with a
Qdrant Query API design merely because an upstream example uses one. Inspect
installed version and mode before applying version-specific advice.
