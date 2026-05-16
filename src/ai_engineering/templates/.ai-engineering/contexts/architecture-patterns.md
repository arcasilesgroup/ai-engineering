# Architecture Patterns

Curated catalog of canonical software architecture patterns. Loaded on-demand by `/ai-plan` to identify the fitting pattern for a spec. The chosen pattern (or `ad-hoc` with explanation) is recorded in `plan.md` under the `## Architecture` section so downstream agents (`/ai-build`, `/ai-verify`, `/ai-review`) inherit the architectural intent without re-deriving it.

This file is NOT preloaded for every skill trigger. Token cost is amortized to `/ai-plan` invocations only. Per-pattern entries follow the same schema (`Description`, `When to use`, `When NOT to use`, `Example`) so consumers can reason about applicability deterministically.

Source: snapshot curated from `https://skills.sh/wshobson/agents/architecture-patterns` and canonical software architecture literature (Fowler, Evans, Vernon, Hohpe). Refresh handled by separate spec when external sources materially change; spec-106 ships the snapshot.

---

## Layered Architecture

**Description**: Layered architecture (also called n-tier) organizes the system into horizontal layers where each layer has a distinct responsibility — typically presentation, business/application, domain, and persistence. Each layer depends only on the layer immediately beneath it, enforcing a top-down dependency direction. The pattern is the default starting point for most enterprise applications because it matches how teams think about responsibility boundaries and is easy to onboard new developers into.

**When to use**:
- Standard CRUD-style enterprise applications with stable, well-understood domains.
- Teams new to architecture patterns who need a low-ceremony default.
- Monolithic applications where horizontal slicing aids team ownership and code review.
- Systems where the persistence model maps closely to the domain model.

**When NOT to use**:
- Domains with deep business invariants where the domain model needs isolation from infrastructure (use hexagonal or clean architecture instead).
- Event-driven or asynchronous workflows where layers create artificial sequencing.
- Systems requiring multiple interchangeable persistence backends — layer coupling makes substitution painful.

**Example**: A payroll system organizes code into a presentation layer (web controllers and DTOs), a service layer (payroll calculation orchestration), a domain layer (Employee, Salary, TaxBracket), and a persistence layer (repositories backed by PostgreSQL). The presentation layer never reaches into persistence directly; it always passes through services, which delegate to the domain layer for business rules and to repositories for persistence.

---

## Hexagonal Architecture

**Description**: Hexagonal architecture (Alistair Cockburn's "ports and adapters") puts the application core at the center and treats every external concern — UI, database, message broker, third-party API — as an adapter that plugs into a port (an interface owned by the core). The core defines what it needs (ports) and adapters implement how those needs are satisfied. Dependencies always point inward: adapters depend on ports, never the other way around.

**When to use**:
- Domains with rich business logic that must be independent of delivery mechanism (REST, CLI, batch, message queue).
- Systems where the same core must serve multiple delivery channels (web app + CLI + scheduled job).
- Teams that want fast, headless tests by swapping adapters for in-memory fakes.
- Long-lived applications where infrastructure is expected to change but the domain is stable.

**When NOT to use**:
- Trivial CRUD applications where the indirection layer adds ceremony without benefit.
- Short-lived prototypes where time-to-market matters more than testability.
- Teams without experience defining clean interfaces — risk of leaky ports that pull infrastructure into the core.

**Example**: An inventory management service defines a `StockRepository` port (interface) and a `NotificationGateway` port. The core domain reduces stock when an order ships and notifies subscribers. In production the adapters are a PostgreSQL `StockRepository` and a Kafka `NotificationGateway`; in tests the adapters are in-memory implementations. The core never imports SQL drivers or Kafka clients — those imports live only in the adapter modules.

---

## CQRS

**Description**: CQRS (Command Query Responsibility Segregation) splits the model into two: a write model that handles commands (state-changing operations) and a read model optimized for queries. The two models can share a database or use entirely separate stores; the key invariant is that commands never return data and queries never mutate state. This separation enables independent scaling, denormalized read views, and clear audit trails for state changes.

**When to use**:
- Read-heavy systems where query patterns differ significantly from the write model (e.g., analytics dashboards, reporting).
- Systems with complex domain logic on writes but simple shape requirements on reads.
- High-throughput applications where read and write workloads need independent scaling and caching.
- Domains where command intent (e.g., `CancelOrder`) is more meaningful than CRUD verbs.

**When NOT to use**:
- Simple CRUD applications where commands and queries operate on identical shapes.
- Small teams that cannot maintain two models without drift between them.
- Latency-sensitive workflows where eventual consistency between write and read models is unacceptable.
- Systems without dedicated infrastructure for projections or read-model rebuilds.

**Example**: An e-commerce platform uses a normalized PostgreSQL write model for orders (`Order`, `OrderLine`, `Customer`) and a denormalized Elasticsearch read model for the customer-facing order history page (single document per order with embedded customer name and product snapshots). When `PlaceOrder` is committed to the write model, an event projector updates the Elasticsearch document. The order history page queries Elasticsearch directly, never the relational store.

---

## Event Sourcing

**Description**: Event sourcing persists every state change as an immutable event in an append-only log. Current state is derived by replaying events from the log; the events ARE the source of truth, not a snapshot of state. This gives perfect audit history, time-travel debugging, and the ability to rebuild any read model by replaying events. Often paired with CQRS where commands produce events and projections build read models from the event stream.

**When to use**:
- Domains where the history of changes matters as much as the current state (banking, healthcare, audit-heavy systems).
- Systems requiring temporal queries ("what did the inventory look like on March 1?").
- Architectures that need to evolve read models without losing data — replay events into the new shape.
- Compliance-driven domains where every state change must be traceable to a triggering event.

**When NOT to use**:
- Domains where current state is all that matters and history is noise (cache stores, ephemeral session data).
- Teams without infrastructure for event versioning, snapshotting, and replay tooling.
- Systems with strict synchronous read-after-write requirements that cannot tolerate projection lag.
- Simple applications where the operational complexity of an event store outweighs the audit benefit.

**Example**: A bank account ledger persists `MoneyDeposited`, `MoneyWithdrawn`, `AccountFrozen`, and `AccountUnfrozen` events. The current balance is computed by folding over the event stream. When a customer requests their balance as of December 31 of the previous tax year, the system replays only events up to that timestamp. A new fraud-detection projection is added later by replaying the entire event log into a new read model — no migration of existing data is needed.

---

## Ports and Adapters

**Description**: Ports and adapters is the structural foundation underpinning hexagonal architecture: the application core declares ports (interfaces) and external systems integrate via adapters that implement those ports. The pattern emphasizes that ports are defined by the needs of the core (driven by the domain language), not by what existing infrastructure happens to provide. Adapters are written to satisfy the port contract, even if that means wrapping or simplifying the underlying technology.

**When to use**:
- When swapping infrastructure (e.g., switching from REST to gRPC, or PostgreSQL to DynamoDB) must not touch business logic.
- Test strategies that rely on substituting fast in-memory adapters for slow real ones.
- Systems where multiple delivery mechanisms (CLI, HTTP, message queue) drive the same domain operations.
- Teams enforcing strict dependency inversion to prevent infrastructure leaking upward.

**When NOT to use**:
- Single-channel applications where the delivery mechanism will never change.
- Code paths where the abstraction layer adds latency the system cannot afford (high-frequency trading, hot loops).
- Teams that conflate ports with DTOs and end up with anemic interfaces that mirror infrastructure 1:1.

**Example**: A document conversion service exposes a `Converter` port with `convert(input, target_format)`. Two adapters exist: a `LibreOfficeAdapter` that shells out to a local LibreOffice install, and a `CloudConverterAdapter` that calls a SaaS API. The core service decides which adapter to use based on configuration, but the calling code only ever sees the `Converter` port. Swapping the cloud provider later requires writing a new adapter; no domain code changes.

---

## Clean Architecture

**Description**: Robert Martin's clean architecture concentrically arranges code in four layers — entities (enterprise rules), use cases (application rules), interface adapters (controllers, presenters, gateways), and frameworks/drivers (web, database, external services). The dependency rule is absolute: dependencies only point inward. Outer layers know about inner layers; inner layers never know about outer ones. The pattern unifies hexagonal, onion, and DCI architectures under a single discipline.

**When to use**:
- Long-lived business systems where the domain model outlives any specific framework or database.
- Teams committed to TDD where use cases must be testable without spinning up the framework.
- Systems requiring clear separation between enterprise-wide rules (entities) and application-specific workflows (use cases).
- Codebases that have suffered from framework lock-in and need a cleaner reset.

**When NOT to use**:
- Small or short-lived applications where the layer count creates more friction than value.
- Frameworks-first projects (e.g., a simple Rails CRUD app) where the framework conventions ARE the architecture.
- Teams without discipline to maintain dependency direction — the pattern collapses if inner layers import from outer ones.

**Example**: A subscription billing system places `Subscription`, `Invoice`, and `Customer` in the entities layer (business rules independent of any application). Use cases like `RenewSubscription` and `IssueRefund` orchestrate entities. Interface adapters translate HTTP requests into use case inputs and use case outputs into HTTP responses. The frameworks layer contains the FastAPI app, the SQLAlchemy session factory, and the Stripe API client. None of the inner layers import FastAPI, SQLAlchemy, or Stripe directly.

---

## Pipes and Filters

**Description**: Pipes and filters decomposes a processing task into a sequence of independent components (filters) connected by channels (pipes). Each filter consumes input, transforms it, and emits output for the next filter; filters know nothing about each other beyond the data contract on the pipe. The pattern produces highly composable, individually testable components and is the structural basis for stream processing, ETL pipelines, and Unix shell composition.

**When to use**:
- Data transformation workflows with clear, stage-able processing steps (ETL, log processing, image pipelines).
- Stream processing where each stage operates independently and can be parallelized.
- Compiler and interpreter pipelines (lex, parse, type-check, optimize, emit).
- Systems where stages need to be reordered, skipped, or replaced based on configuration.

**When NOT to use**:
- Workflows requiring shared mutable state across stages — pipes enforce isolation that becomes painful here.
- Latency-critical paths where the per-stage marshaling overhead is unacceptable.
- Domains where stages have complex back-and-forth dependencies that linear pipes cannot express.

**Example**: A data ingestion pipeline reads CSV files (filter 1: parse), validates rows against a schema (filter 2: validate), enriches with external API lookups (filter 3: enrich), deduplicates (filter 4: dedupe), and writes to a data warehouse (filter 5: load). Each filter is a separate process or function. Adding a new transformation (filter 2.5: normalize phone numbers) requires inserting a filter between validate and enrich without touching either neighbor.

---

## Repository

**Description**: The repository pattern mediates between the domain and the data-mapping layer by exposing collection-like access to aggregates. Domain code asks the repository for objects (`getById`, `findByCriteria`, `save`) without knowing whether the underlying store is SQL, NoSQL, or in-memory. Repositories enforce that aggregates are loaded and persisted as a unit, preserving aggregate boundaries declared in domain-driven design.

**When to use**:
- Domain-driven design contexts where aggregates are first-class and must be loaded transactionally.
- Codebases where multiple persistence technologies (e.g., relational write store + search index read store) coexist.
- Test strategies that swap real repositories for in-memory implementations to keep tests fast and deterministic.
- Systems where the persistence model evolves separately from the domain model.

**When NOT to use**:
- Simple CRUD applications where direct ORM use is more honest about what the code does.
- Read-heavy systems with complex queries — repositories often degrade into anemic facades over the ORM. Use direct queries or CQRS read models instead.
- Domains without aggregates where the repository abstraction adds noise without clarifying intent.

**Example**: An order management domain defines an `OrderRepository` with `getById(orderId): Order`, `findByCustomer(customerId): list[Order]`, and `save(order: Order): None`. A SQLAlchemy implementation loads `Order` with its `OrderLines` in a single query, returns a fully hydrated aggregate, and `save` upserts the aggregate transactionally. Domain code never imports SQLAlchemy; it depends only on the `OrderRepository` interface.

---

## Unit of Work

**Description**: The unit-of-work pattern tracks a set of changes to multiple aggregates and commits them as a single atomic transaction. It pairs with the repository pattern: repositories register dirty aggregates with the unit of work, and the unit of work flushes all changes at commit. The pattern keeps transaction boundaries explicit at the application layer instead of leaking them into individual repositories or the domain.

**When to use**:
- Workflows that mutate multiple aggregates and need atomic commit semantics.
- Domain-driven design contexts where the unit of work boundary corresponds to a use case or command handler.
- Codebases that must support transparent transaction handling without sprinkling `commit/rollback` everywhere.
- Systems where retry logic, idempotency, or saga compensation needs a clear transaction boundary to anchor on.

**When NOT to use**:
- Single-aggregate operations where the repository's own transaction handling is enough.
- Eventual-consistency architectures where multi-aggregate commits are intentionally avoided.
- Distributed systems where the unit of work would span multiple bounded contexts — use sagas or process managers instead.

**Example**: A bank transfer use case loads two `Account` aggregates (debit source, credit destination), debits one, credits the other, and registers both with the unit of work. On `commit`, the unit of work issues a single transaction that updates both accounts atomically. If either update fails, both roll back. Domain code never sees the SQL transaction; it only knows it has a unit of work scope from the use case entry point to its return.

---

## Microservices

**Description**: Microservices decomposes an application into a set of small, independently deployable services, each owning a bounded context (a domain slice with its own data and rules). Services communicate over the network via APIs (REST, gRPC) or events (message broker). Each service can be developed, deployed, scaled, and replaced independently, enabling team autonomy and technology heterogeneity at the cost of distributed-system complexity.

**When to use**:
- Organizations where multiple teams need to ship independently without coordinating release trains.
- Systems with bounded contexts that have genuinely different scaling, availability, or technology requirements.
- Mature engineering organizations with platform support for service discovery, observability, and CI/CD.
- Domains where some components must evolve at very different cadences (e.g., billing core stable for years, recommendation engine iterated weekly).

**When NOT to use**:
- Small teams where the operational overhead of running many services exceeds the benefit of independent deployment.
- Greenfield products where bounded contexts are not yet understood — premature decomposition produces wrong service boundaries.
- Systems requiring strong cross-domain transactional consistency that distributed transactions cannot sanely provide.
- Organizations without observability, deployment automation, or platform engineering investment to operate dozens of services.

**Example**: An e-commerce platform has separate services for catalog, cart, checkout, order management, fulfillment, payments, and notifications. Each owns its database. The checkout service calls catalog (read product details) and payments (charge card) over REST, then publishes an `OrderPlaced` event. The order management service consumes the event and writes to its own datastore. A failure in notifications never blocks checkout because the boundary is asynchronous.

---

## Modular Monolith

**Description**: A modular monolith is a single deployable application internally organized into well-defined modules, each owning a bounded context with strict module boundaries enforced at the code level (e.g., compile-time visibility rules, package access). It captures most of the architectural benefits of microservices — clear context boundaries, team ownership, replaceable internals — without paying the operational cost of running and orchestrating multiple services. Modules can later be extracted into services if the boundary proves stable.

**When to use**:
- Teams or organizations not yet ready for microservice operational complexity but wanting clean context boundaries.
- New systems where bounded contexts are still being discovered — keep options open by deferring deployment-time decomposition.
- Mid-sized applications where the monolith fits a single operational footprint but the codebase needs internal structure.
- Migration paths from a tangled monolith to microservices: modularize first, extract later.

**When NOT to use**:
- Systems where independent deployment of modules is a hard requirement (different release cadences, scaling profiles, availability SLAs).
- Codebases without language or build-system support for enforcing module boundaries — boundaries that depend on developer discipline alone tend to erode.
- Domains where modules genuinely need different runtimes or technology stacks that cannot coexist in one process.

**Example**: A SaaS billing platform is a single Spring Boot application with internal Maven modules for `customers`, `subscriptions`, `invoicing`, `payments`, and `notifications`. Each module exposes a small public API (Java package-private discipline plus ArchUnit tests) and hides everything else. Cross-module communication goes through these public APIs, never internal classes. When `payments` outgrows the monolith and needs independent scaling, it is extracted into its own service with minimal call-site changes because callers already only knew the public API.
