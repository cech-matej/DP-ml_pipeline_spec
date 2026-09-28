# Cascade and phase policies

The cascade is outside the classifier implementation.

## Cascade YAML reference

The example is orchestration metadata only; it does not cause collection or execute the cascade by itself.

### `cascade.name`

Stable logical name of the example cascade/orchestration definition.

### `cascade.version`

Version of the cascade definition. Increment it when phase ordering, membership or orchestration semantics change.

### `phases[].name`

Logical name of a phase that the future orchestration layer may call.

### `phases[].microservice`

Optional service identifier used when the phase is exposed as a concrete microservice. In the example, `html-phase` is the deployable service name for the HTML phase.

### `phases[].information_boundary`

The information boundary expected to be available when that phase is called. This is an orchestration-level declaration of what evidence the phase consumes; it does not instruct the phase to collect it.

## Current cascade manifest

`configs/cascades/production-example.yaml` is deliberately an orchestration example. It lists lexical, DNS, TLS/RDAP and HTML boundaries and maps the HTML phase to the `html-phase` microservice. The future THOR flow decides when each phase is called.

A future implementation may add explicit routing/gate rules here or, more appropriately for THOR V1, keep those decisions in the THOR rule/gate layer.

## Cascade

A future orchestration layer can contain ordered phases:

```text
prefilter
   |
lexical
   |
DNS/geo
   |
TLS/RDAP
   |
HTML phase
   |
AI/agent phase
```

THOR V1 describes the same general pattern: ordered steps with gates that allow early verdicts and escalate remaining domains to more expensive steps.

## Phase with multiple classifiers

```text
HTML phase
  |
  +-- HTML/JS classifier
  +-- DOM/phishing fingerprint classifier
  +-- DGA-related detector (if applicable)
  |
  v
phase policy
```

Classifiers may be executed in parallel after their feature vectors are ready.

## Phase policy

A phase policy can translate heterogeneous results into a phase-level outcome:

```yaml
policy:
  type: rule_based

  outputs:
    - phishing
    - malware
    - benign
    - uncertain

  rules:
    - when:
        classifier: dom-phishing
        field: score
        operator: gte
        value: 0.95
      emit:
        label: phishing

    - when:
        classifier: dga
        field: score
        operator: gte
        value: 0.95
      emit:
        label: dga

  otherwise: uncertain
```

These thresholds are configuration examples, not validated recommendations.

The policy must not assume every classifier is binary.

## Responsibility boundary

The phase may say:

```text
phishing with confidence 0.96
```

The orchestration layer decides:

```text
stop and emit verdict
```

or:

```text
collect next information boundary
```

Therefore collection decisions and collection-cost metrics belong outside the ML phase.
