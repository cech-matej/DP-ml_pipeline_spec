# Phase scaling and batching

## Goals

The deployment model supports both:

1. multiple domains per request; and
2. multiple instances of the same phase.

These are separate mechanisms and can be tuned independently.

## Batch size

The service contract contains `domains[]`. Every item has a `domain_id` and its input facts.

A request containing 100 domains is still one transport message, but the phase should not be required to process all 100 simultaneously.

`execution.max_concurrent_domains` bounds per-instance domain concurrency.

## Horizontal replicas

A phase can run as N identical instances.

For HTTP:

```text
                 load balancer
                 /     |     \
                /      |      \
       instance-1  instance-2  instance-3
```

For Kafka:

```text
                 input topic
                /     |     \
               /      |      \
          consumer  consumer  consumer
          instance  instance  instance
               \      |      /
                \     |     /
                 output topic
```

Kafka replicas of the same phase share the same consumer group. They must have sufficient topic partitions to make additional replicas useful.

## Uneven replica counts by pipeline depth

Replica count is configured per deployed phase, not globally for the ML package.

For example, a deployment may intentionally use many instances for an early, high-volume phase and fewer instances for a later phase reached by only a subset of domains.

```text
                    domain volume

Phase 1     ████████████████████    12 instances
Phase 2     ███████████              8 instances
Phase 3     ███                      3 instances
Phase 4     █                        1 instance
```
_Those numbers are illustrative, not recommended values._

The ML phase code does not contain assumptions about the number of replicas.

## Resource planning

The useful capacity of a phase depends on:

- average domains per request;
- `max_concurrent_domains`;
- classifier concurrency;
- feature extraction cost;
- explanation cost when enabled;
- number of replicas;
- Kafka partition count when Kafka is used;
- available CPU/GPU/memory.

Measure these independently before choosing replica counts.

## Backpressure

The transport/deployment layer should provide backpressure rather than allowing unbounded in-process work. In particular, a large Kafka backlog should not cause one phase instance to create an unbounded number of threads.
