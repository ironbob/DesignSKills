# Trust And Lifecycle Simplification

Load this reference only for defensive copies, freezes, validators, callback capture, or complex asynchronous lifecycle machinery.

## Trust Boundaries

For every defense, identify the value's origin and next owner.

- Same-process typed service or plugin calls ordinarily borrow readonly values.
- Parsers, config loaders, queues, model/tool JSON, durable files, workers, processes, and wire decoders own or validate their input.
- Tests using hostile getters, fake typed objects, callback replacement, or mutation after a same-process handoff may describe a speculative contract; they are not automatic justification for retaining it.

Propose removal only after confirming that no real boundary, public contract, or recorded defensive pattern requires the behavior.

## Lifecycle Ownership

Draw the ownership/transition graph for complex async code. Map every sentinel, readiness promise, cancellation path, disposer, callback, and state flag to a distinct owner or transition.

Several mechanisms that encode the same liveness or settlement fact are candidates for one transaction or lifecycle controller. Preserve separate machinery when it independently protects:

- synchronous publication and rollback;
- callback containment;
- first-terminal-outcome arbitration;
- worker or process ownership;
- dispose-to-quiescence.

The proposal must name which facts collapse and why the remaining controller still owns every terminal path.
