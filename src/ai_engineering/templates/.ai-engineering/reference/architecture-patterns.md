# Architecture Patterns

Curated catalog of canonical software architecture patterns. Loaded on-demand by `/ai-plan` (not preloaded per skill trigger — token cost is amortized to `/ai-plan` only) to pick the fitting pattern for a spec. The chosen pattern (or `ad-hoc` with explanation) is recorded in `plan.md` under `## Architecture` so `/ai-build`, `/ai-verify`, and `/ai-review` inherit the intent without re-deriving it.

Every entry follows the same schema (`Description`, `When to use`, `When NOT to use`, `Example`) for deterministic applicability reasoning. Source: snapshot curated from `https://skills.sh/wshobson/agents/architecture-patterns` and canonical literature (Fowler, Evans, Vernon, Hohpe); spec-106 ships the snapshot, refreshed by a separate spec when sources materially change.

---

## Layered Architecture

**Description**: Layered (n-tier) architecture organizes the system into horizontal layers — typically presentation, business/application, domain, and persistence — each depending only on the layer beneath it. It is the default starting point for enterprise apps: it matches how teams reason about responsibility boundaries and is easy to onboard new developers into.

**When to use**:
- Standard CRUD enterprise apps with stable, well-understood domains.
- Teams new to architecture patterns needing a low-ceremony default.
- Monoliths where horizontal slicing aids team ownership and code review.
- Systems where the persistence model maps closely to the domain model.

**When NOT to use**:
- Deep business invariants needing domain isolation from infrastructure (use hexagonal or clean instead).
- Event-driven or async workflows where layers force artificial sequencing.
- Multiple interchangeable persistence backends — layer coupling makes substitution painful.

**Example**: A payroll system splits into presentation (web controllers, DTOs), service (payroll orchestration), domain (Employee, Salary, TaxBracket), and persistence (PostgreSQL repositories). Presentation never reaches persistence directly — it goes through services, which delegate to the domain for rules and to repositories for storage.

---

## Hexagonal Architecture

**Description**: Hexagonal architecture (Cockburn's "ports and adapters") puts the application core at the center and treats every external concern — UI, database, message broker, third-party API — as an adapter that plugs into a port (an interface owned by the core). Dependencies always point inward: adapters depend on ports, never the other way around.

**When to use**:
- Rich business logic that must stay independent of delivery mechanism (REST, CLI, batch, queue).
- One core serving multiple delivery channels (web + CLI + scheduled job).
- Fast, headless tests by swapping adapters for in-memory fakes.
- Long-lived apps where infrastructure changes but the domain is stable.

**When NOT to use**:
- Trivial CRUD where the indirection is pure ceremony.
- Short-lived prototypes where time-to-market beats testability.
- Teams inexperienced with clean interfaces — risk of leaky ports pulling infrastructure into the core.

**Example**: An inventory service defines a `StockRepository` port and a `NotificationGateway` port. The core reduces stock when an order ships and notifies subscribers. Production adapters are a PostgreSQL `StockRepository` and a Kafka `NotificationGateway`; tests use in-memory ones. The core never imports SQL drivers or Kafka clients — those live only in adapter modules.

---

## CQRS

**Description**: CQRS (Command Query Responsibility Segregation) splits the model in two: a write model that handles state-changing commands and a read model optimized for queries. They may share a database or use separate stores; the invariant is that commands never return data and queries never mutate state. This enables independent scaling, denormalized read views, and clear audit trails.

**When to use**:
- Read-heavy systems where query patterns differ sharply from the write model (dashboards, reporting).
- Complex write-side domain logic but simple read shapes.
- High-throughput apps needing independent read/write scaling and caching.
- Domains where command intent (`CancelOrder`) is more meaningful than CRUD verbs.

**When NOT to use**:
- Simple CRUD where commands and queries share identical shapes.
- Small teams that cannot maintain two models without drift.
- Latency-sensitive flows that cannot tolerate eventual consistency between models.
- Systems without infrastructure for projections or read-model rebuilds.

**Example**: An e-commerce platform uses a normalized PostgreSQL write model (`Order`, `OrderLine`, `Customer`) and a denormalized Elasticsearch read model for the customer-facing order-history page. When `PlaceOrder` commits, an event projector updates the Elasticsearch document. The history page queries Elasticsearch directly, never the relational store.

---

## Event Sourcing

**Description**: Event sourcing persists every state change as an immutable event in an append-only log; current state is derived by replaying events, so the events ARE the source of truth, not a snapshot. This yields perfect audit history, time-travel debugging, and the ability to rebuild any read model by replaying. Often paired with CQRS, where commands produce events and projections build read models.

**When to use**:
- Domains where change history matters as much as current state (banking, healthcare, audit-heavy).
- Systems needing temporal queries ("what did inventory look like on March 1?").
- Architectures that evolve read models by replaying events into a new shape.
- Compliance domains where every change must trace to a triggering event.

**When NOT to use**:
- Domains where only current state matters and history is noise (caches, ephemeral sessions).
- Teams lacking event-versioning, snapshotting, and replay tooling.
- Strict synchronous read-after-write needs that cannot tolerate projection lag.
- Simple apps where an event store's operational cost outweighs the audit benefit.

**Example**: A bank account ledger persists `MoneyDeposited`, `MoneyWithdrawn`, `AccountFrozen`, and `AccountUnfrozen` events; the balance is a fold over the stream. A prior-tax-year balance replays events only up to that timestamp. A fraud-detection projection is added later by replaying the whole log into a new read model — no data migration.

---

## Ports and Adapters

**Description**: Ports and adapters is the structural foundation under hexagonal architecture: the core declares ports (interfaces) and external systems integrate via adapters that implement them. Crucially, ports are defined by the core's needs (its domain language), not by what existing infrastructure provides; adapters are written to satisfy the port contract, even when that means wrapping or simplifying the underlying technology.

**When to use**:
- Swapping infrastructure (REST→gRPC, PostgreSQL→DynamoDB) must not touch business logic.
- Test strategies substituting fast in-memory adapters for slow real ones.
- Multiple delivery mechanisms (CLI, HTTP, queue) driving the same domain operations.
- Strict dependency inversion to keep infrastructure from leaking upward.

**When NOT to use**:
- Single-channel apps where the delivery mechanism will never change.
- Hot paths where the abstraction adds unaffordable latency (high-frequency trading, tight loops).
- Teams that conflate ports with DTOs, ending up with anemic interfaces mirroring infrastructure 1:1.

**Example**: A document-conversion service exposes a `Converter` port with `convert(input, target_format)`. A `LibreOfficeAdapter` shells out to a local install; a `CloudConverterAdapter` calls a SaaS API. The service picks an adapter by configuration, but callers only see the `Converter` port. Swapping the cloud provider later means writing a new adapter — no domain code changes.

---

## Clean Architecture

**Description**: Robert Martin's clean architecture arranges code in four concentric layers — entities (enterprise rules), use cases (application rules), interface adapters (controllers, presenters, gateways), and frameworks/drivers (web, database, external services). The dependency rule is absolute: dependencies point only inward; outer layers know inner ones, never the reverse. It unifies hexagonal, onion, and DCI architectures under one discipline.

**When to use**:
- Long-lived business systems where the domain outlives any framework or database.
- TDD teams needing use cases testable without spinning up the framework.
- Clear separation of enterprise-wide rules (entities) from application workflows (use cases).
- Codebases recovering from framework lock-in that need a cleaner reset.

**When NOT to use**:
- Small or short-lived apps where the layer count adds friction over value.
- Frameworks-first projects (a simple Rails CRUD app) where the conventions ARE the architecture.
- Teams without discipline to maintain dependency direction — the pattern collapses if inner imports outer.

**Example**: A subscription-billing system places `Subscription`, `Invoice`, and `Customer` in the entities layer; `RenewSubscription` and `IssueRefund` are use cases orchestrating entities. Interface adapters translate HTTP requests into use-case I/O. The frameworks layer holds the FastAPI app, the SQLAlchemy session factory, and the Stripe client — none imported by the inner layers.

---

## Pipes and Filters

**Description**: Pipes and filters decomposes a processing task into a sequence of independent filters connected by pipes. Each filter consumes input, transforms it, and emits output for the next; filters know nothing of each other beyond the pipe's data contract. The result is composable, individually testable components — the structural basis for stream processing, ETL pipelines, and Unix shell composition.

**When to use**:
- Data-transformation workflows with clear, stage-able steps (ETL, log processing, image pipelines).
- Stream processing where each stage runs independently and can be parallelized.
- Compiler and interpreter pipelines (lex, parse, type-check, optimize, emit).
- Systems where stages are reordered, skipped, or replaced based on configuration.

**When NOT to use**:
- Workflows needing shared mutable state across stages — pipes enforce painful isolation here.
- Latency-critical paths where per-stage marshaling overhead is unacceptable.
- Domains where stages have complex back-and-forth dependencies linear pipes cannot express.

**Example**: A data-ingestion pipeline parses CSV files (filter 1), validates rows against a schema (2), enriches with external API lookups (3), deduplicates (4), and loads to a warehouse (5). Each filter is a separate function or process. Inserting a phone-normalization filter between validate and enrich touches neither neighbor.

---

## Repository

**Description**: The repository pattern mediates between the domain and the data-mapping layer by exposing collection-like access to aggregates (`getById`, `findByCriteria`, `save`). Domain code asks for objects without knowing whether the store is SQL, NoSQL, or in-memory. Repositories enforce that aggregates load and persist as a unit, preserving the aggregate boundaries declared in domain-driven design.

**When to use**:
- DDD contexts where aggregates are first-class and must load transactionally.
- Codebases mixing persistence technologies (relational write store + search read store).
- Test strategies swapping real repositories for in-memory ones to stay fast and deterministic.
- Systems where the persistence model evolves separately from the domain model.

**When NOT to use**:
- Simple CRUD where direct ORM use is more honest about what the code does.
- Read-heavy systems with complex queries — repositories degrade into anemic ORM facades; use direct queries or CQRS read models.
- Domains without aggregates, where the abstraction adds noise without clarifying intent.

**Example**: An order domain defines an `OrderRepository` with `getById`, `findByCustomer`, and `save`. A SQLAlchemy implementation loads `Order` with its `OrderLines` in one query, returns a fully hydrated aggregate, and upserts transactionally. Domain code depends only on the `OrderRepository` interface, never importing SQLAlchemy.

---

## Unit of Work

**Description**: The unit-of-work pattern tracks a set of changes to multiple aggregates and commits them as a single atomic transaction. It pairs with repositories: they register dirty aggregates with the unit of work, and it flushes all changes at commit. The pattern keeps transaction boundaries explicit at the application layer instead of leaking them into individual repositories or the domain.

**When to use**:
- Workflows that mutate multiple aggregates and need atomic commit semantics.
- DDD contexts where the unit-of-work boundary maps to a use case or command handler.
- Codebases wanting transparent transaction handling without scattered `commit/rollback`.
- Systems where retry, idempotency, or saga compensation needs a clear transaction boundary to anchor on.

**When NOT to use**:
- Single-aggregate operations where the repository's own transaction handling suffices.
- Eventual-consistency architectures that intentionally avoid multi-aggregate commits.
- Distributed systems where the boundary would span bounded contexts — use sagas or process managers.

**Example**: A bank-transfer use case loads two `Account` aggregates, debits one, credits the other, and registers both with the unit of work. On commit it issues a single transaction updating both accounts atomically; if either update fails, both roll back. Domain code never sees the SQL transaction — only a unit-of-work scope from entry to return.

---

## Microservices

**Description**: Microservices decomposes an application into small, independently deployable services, each owning a bounded context with its own data and rules. Services communicate over the network via APIs (REST, gRPC) or events. Each can be developed, deployed, scaled, and replaced independently — enabling team autonomy and technology heterogeneity at the cost of distributed-system complexity.

**When to use**:
- Multiple teams shipping independently without coordinating release trains.
- Bounded contexts with genuinely different scaling, availability, or technology needs.
- Mature orgs with platform support for service discovery, observability, and CI/CD.
- Components that must evolve at very different cadences (stable billing vs. weekly recommendations).

**When NOT to use**:
- Small teams where running many services costs more than independent deployment is worth.
- Greenfield products with undiscovered bounded contexts — premature decomposition yields wrong boundaries.
- Systems requiring strong cross-domain transactional consistency that distributed transactions cannot sanely provide.
- Orgs lacking observability, deployment automation, or platform engineering to run dozens of services.

**Example**: An e-commerce platform runs separate services for catalog, cart, checkout, order management, fulfillment, payments, and notifications, each owning its database. Checkout calls catalog and payments over REST, then publishes an `OrderPlaced` event; order management consumes it into its own store. A notifications failure never blocks checkout because the boundary is asynchronous.

---

## Modular Monolith

**Description**: A modular monolith is a single deployable application internally split into well-defined modules, each owning a bounded context with boundaries enforced at the code level (compile-time visibility rules, package access). It captures most microservice benefits — clear boundaries, team ownership, replaceable internals — without the operational cost of running many services. Modules can later extract into services if the boundary proves stable.

**When to use**:
- Teams wanting clean context boundaries but not ready for microservice operational complexity.
- New systems where bounded contexts are still being discovered — defer deployment-time decomposition.
- Mid-sized apps that fit one operational footprint but need internal structure.
- Migration paths from a tangled monolith to microservices: modularize first, extract later.

**When NOT to use**:
- Systems where independent deployment of modules is a hard requirement (different cadences, scaling, SLAs).
- Codebases without language or build-system support to enforce boundaries — discipline-only boundaries erode.
- Domains where modules genuinely need different runtimes or stacks that cannot coexist in one process.

**Example**: A SaaS billing platform is a single Spring Boot app with Maven modules for `customers`, `subscriptions`, `invoicing`, `payments`, and `notifications`. Each exposes a small public API (package-private discipline plus ArchUnit tests); cross-module calls go through it, never internal classes. When `payments` needs independent scaling, it extracts into its own service with minimal call-site changes.
