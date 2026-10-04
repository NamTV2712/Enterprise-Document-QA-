# Threat model and review

Treat retrieved text and metadata as attacker-controlled data. Trace trust from
SEC URL and filing through parser, chunk/index, retrieval, context, prompt,
rendering, persistence, logs, and exports. Include source impersonation,
cross-document identity confusion, prompt-boundary confusion, poisoning, and
citation substitution in review cases.
