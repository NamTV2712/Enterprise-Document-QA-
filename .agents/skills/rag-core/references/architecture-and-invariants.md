# Architecture and invariants

The project flow is:

```text
question -> submitted scope -> retrieval -> selected evidence -> generation
-> answer version -> citation -> source -> indexed chunk -> filing/document
-> canonical revision -> evidence location
```

Keep inspection, generation, source viewing, and evaluation as distinct paths.
Resolve scope and identity at the operation boundary and reject stale updates.
Document implementation truth when it differs from historical documentation.
