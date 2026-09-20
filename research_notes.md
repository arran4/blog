# Research Notes: Scenarios, Fixtures, and Verification

These notes record repository-specific findings from investigating the scenario, fixture, and verification architectures across the Arran4 ecosystem, as requested.

## Repository Findings

### arran4/goa4web
- **Scenario Implementation:** Utilises a TXTAR-based format (`goa4web-scenario/v1`) to define scenarios as executable application state.
- **Key Features:** Uses an Operation Registry mapping string operation names (e.g., `user.create`, `forum.post`) to typed application functions. Relies heavily on symbolic references rather than generated database IDs, ensuring portability.
- **Target Environments:** Can apply scenarios to both persistent databases and ephemeral, disposable SQLite instances. Includes a CLI (`scenario serve`) to boot a disposable server instantly populated by a scenario, completely isolated from production side-effects.

### arran4/gobookmarks
- **Verification Views:** Implements a robust `verification template` command.
- **Key Features:** Supports named cases, synthetic request generation, and JSON data input for fast, isolated template rendering. Allows narrow template function overrides to stub out persistence where full scenario backing is overkill.
- **Simpler Domain:** Unlike Goa4Web's complex forum graphs, GoBookmarks benefits from a simpler domain (URLs, tags). Scenarios here can be less event-oriented and more declarative.

### arran4/address
- **Domain:** Focuses on users, addresses, effective dates, and companies.
- **Scenario Adaptation:** An in-memory repository implementation would be ideal here to support scenarios without coupling them to SQLite or Datastore. Operations would reflect domain verbs (e.g., `address.move`, `user.link_company`) rather than generic CRUD, using typed references for people and locations.

### arran4/mail
- **Domain:** Email parsing, mbox import, and persistence.
- **Scenario Adaptation:** A text-based event log (like TXTAR) is likely the wrong abstraction for email states. A directory containing real RFC message files (`.eml` or mbox) with a small manifest is a more native, appropriate scenario representation. The principle remains standardising the lifecycle, not the syntax.

### arran4/userforum
- **Fixture DSL:** Uses a Go-native, strongly typed mock-data/fixture builder system.
- **Key Features:** Relies on a typed operation/factory style for constructing nested forums, threads, and posts. Supports relative reply/fork semantics and invariant checking of the constructed graph.
- **Comparison:** This is an alternative to external scenario files. Typed DSLs and portable external scenarios solve overlapping problems; a strongly typed builder can even compile *into* an external scenario format.

### arran4/InkFalls
- **Domain:** (Deduced) Content management or similar persistence-backed domain.
- **Scenario Adaptation:** Scenario-driven state construction must prove it adds value over the existing domain persistence abstractions. If the native abstraction is simpler, that should be preferred over forcing a uniform scenario format everywhere.

---

# Draft Outline: Fixture DSLs (Future Article)

**Title:** Typed Fixture DSLs and Builders: Constructing State in Code

**1. Introduction**
- The limits of external text scenarios (refactoring, compile-time safety).
- When to use a Go-native, strongly typed builder system.

**2. Designing a Typed Option/Builder DSL**
- Using functional options and builder patterns to configure entities.
- Readability vs. verbosity in test code.

**3. Factories and Graph Construction**
- Managing nested construction (e.g., Forum -> Thread -> Post).
- Handling deferred parent references elegantly.
- Relative references: expressing intent like "reply to previous post" without tracking IDs.

**4. Determinism and Integrity**
- Ensuring deterministic IDs and time within the DSL.
- Invariant checking: verifying the constructed graph makes sense before saving it (e.g., ensuring a thread actually belongs to the forum it claims).

**5. Compiling DSLs to Scenarios**
- The overlap between typed DSLs and external scenario files.
- The possibility of using a typed DSL in Go to generate/compile an intermediate representation that can be saved as a portable scenario file.

**6. Conclusion**
- Choose the tool based on the consumer: DSLs for Go developers and compile-time safety; external scenarios for portability, CI, and agents.