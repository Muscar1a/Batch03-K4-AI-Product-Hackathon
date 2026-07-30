# OdysseyBot Full Refactor — Exporter-Sidecar Architecture

## Summary

Create branch `Thanh` from the current clean `nhat_langraph-bot` commit `4494746`.

```bash
git switch nhat_langraph-bot
git switch -c Thanh
git push -u origin Thanh
```

The program Discord is on a server where the bot cannot be installed. Therefore, split the system into two independent paths:

```text
Program Discord
  → isolated DiscordChatExporter job using user token
  → validated JSON artifact
  → SQLite importer
  → FTS5 + NetworkX projection
  → LangGraph assistant
  → bot on personal prototype Discord
```

The bot responds in realtime on the personal server, but program-server knowledge is refreshed daily. The exporter is deterministic infrastructure, not an LLM tool.

A Discord user token was exposed in `session-ses_04f1.md`. Before implementation, revoke/rotate that token. The file is currently ignored by Git, but must be sanitized or deleted after extracting non-sensitive notes.

## Stack Decision

Use:

- Python 3.12 and `uv`.
- `discord.py` for the bot on the personal server.
- DiscordChatExporter.Cli `v2.47.3` as an isolated source adapter.
- LangGraph with Gemini for grounded answer orchestration.
- SQLite WAL + FTS5 via `aiosqlite` as the durable store.
- NetworkX as a rebuildable graph projection, not persistence.
- Async `httpx` adapters for Tavily and Firecrawl.
- Pydantic Settings for validated configuration.
- Pytest, pytest-asyncio, coverage, and Ruff.

Do not add Neo4j, Postgres, Redis, a vector database, frontend, or multi-agent swarm.

Automating a Discord user account may violate Discord policy and can lead to account suspension. The architecture will isolate and disable that path easily, but cannot eliminate this external policy risk. An authorized read-only bot on the program server remains the preferred future replacement.

## Source Ingestion Architecture

### Exporter sidecar

Define a deep `ProgramArchiveSync` module:

```python
class ProgramArchiveSync:
    async def run_incremental(self) -> SyncResult: ...
    async def run_full_snapshot(self) -> SyncResult: ...
    async def status(self) -> SyncStatus: ...
```

Its implementation owns:

- Thread discovery.
- Exporter subprocess execution.
- Cursor handling.
- Rate-limit and timeout behavior.
- Staging directories.
- Artifact validation.
- Checksums and completion markers.
- Import coordination.
- Sync logs without credentials.

The LangGraph agent cannot call this interface. Only the scheduler and restricted operations commands can enqueue a predefined sync.

### Credential isolation

Use separate credentials:

- `DISCORD_BOT_TOKEN`: bot account on the personal server.
- `DCE_USER_TOKEN`: read-only export credential for the program server.

When launching DiscordChatExporter:

- Pass `DCE_USER_TOKEN` to the child process as its `DISCORD_TOKEN` environment variable.
- Never pass the token with `--token`.
- Never include it in command output, exceptions, metrics, process arguments, SQLite, or docs.
- Give the child a minimal environment.
- Run it under a dedicated OS user/container.
- Restrict secret-file permissions to `0600`.
- Restrict writable paths to the export staging directory.
- Add `DCE_SYNC_ENABLED=false` as an immediate kill switch.
- Stop immediately on authentication errors.
- Back off and abort on repeated `429`, `401`, or `403` responses.
- Never retry indefinitely.

The exporter command is fixed by configuration. The agent cannot supply arbitrary flags, output paths, shell fragments, filters, or channel IDs.

### Daily schedule

- Start incremental export at 17:30 Asia/Ho_Chi_Minh.
- Generate the TA/Admin digest at 18:00.
- If the 17:30 sync is still running or fails, publish the digest using the latest successful snapshot and display:
  - Last successful source timestamp.
  - Current sync state.
  - Whether the digest may be stale.
- Do not block the digest indefinitely.
- Run a weekly full reconciliation Sunday at 02:00 to detect edits, deletions, missed messages, and manifest drift.
- Run a startup health check, but do not automatically perform a full export at every restart.

### Incremental export

Maintain a successful-sync cursor in SQLite.

For each daily run:

1. Compute `after = last_successful_source_timestamp - 15 minutes`.
2. Export configured forum parents and known thread IDs using:
   - JSON format.
   - UTC timestamps.
   - Rate-limit respect enabled.
   - Media download disabled.
   - Maximum parallelism `2`.
3. Upsert messages by `(source_guild_id, message_id)`.
4. Deduplicate overlap using message IDs and content hashes.
5. Update the cursor only after export validation and successful SQLite commit.

The overlap captures messages near the previous boundary. The weekly full snapshot handles older edits and deletions that incremental `--after` exports cannot observe.

### Atomic artifact lifecycle

Use ignored runtime paths:

```text
data/runtime/
├── source-sync/
│   ├── staging/<run_id>.partial/
│   ├── ready/<run_id>/
│   ├── imported/<run_id>/
│   └── failed/<run_id>/
├── manifests/
└── odysseybot.sqlite3
```

Workflow:

1. Export into `.partial`.
2. Validate every JSON document.
3. Produce `manifest.json` containing run ID, timestamps, exporter version, source channel IDs, file counts, message counts, and SHA-256 checksums.
4. Atomically rename the directory to `ready`.
5. Import the complete artifact in one SQLite transaction.
6. Move it to `imported` only after commit.
7. Preserve failed artifacts with a sanitized error record.
8. Retain imported artifacts for seven days, then remove them after database backup verification.

A partial export must never become searchable knowledge.

## Thread Discovery

Use a two-level strategy.

### Primary: exporter capability probe

For each configured forum parent in `DCE_FORUM_CHANNEL_IDS`:

- Probe DiscordChatExporter with `--include-threads All`.
- Confirm that known active and archived thread IDs appear.
- Record exporter version and probe result.
- If successful, merge discovered IDs into the manifest.
- Never remove an existing thread ID merely because one probe omitted it.

### Fallback: persisted manifest

Maintain:

```text
data/runtime/manifests/program_threads.json
```

Each entry contains:

- Thread ID.
- Parent forum ID.
- First-seen timestamp.
- Last-successful-export timestamp.
- Active/missing/deleted state.
- Discovery method.

Seed it from the existing thread-ID list produced by the prior search workflow.

If the capability probe cannot enumerate archived threads:

- Continue exporting the persisted manifest.
- Mark discovery as degraded.
- Include a warning in the staff digest.
- Allow an authorized operator to add a numeric thread ID through a fixed CLI/admin command.
- Validate the ID by attempting a single-channel export before saving it.
- Do not automate the unofficial Discord search endpoint on every run.
- Do not expose raw search or arbitrary channel export as an LLM tool.

## Canonical Package

Remove duplicate root `src/` and keep one package:

```text
codebase/
├── pyproject.toml
├── uv.lock
├── .python-version
├── .env.example
├── src/odysseybot/
│   ├── app.py
│   ├── config.py
│   ├── domain/
│   ├── agent/
│   ├── knowledge/
│   ├── ingestion/
│   │   ├── archive_sync.py
│   │   ├── dce_adapter.py
│   │   ├── artifact_importer.py
│   │   ├── authority.py
│   │   └── thread_manifest.py
│   ├── tools/
│   ├── adapters/
│   ├── jobs/
│   └── cli.py
└── tests/
```

The current branch’s circular `src.graph_db.graph_store` wrapper must be removed rather than supported.

## Knowledge and Question Model

SQLite stores:

- `source_messages`: imported program-server messages and role snapshots.
- `bot_messages`: personal-server student and bot interactions.
- `source_runs`: exporter status, checksums, timing, errors, and freshness.
- `source_threads`: persisted thread manifest.
- `sync_cursors`: incremental and full-sync cursors.
- `questions`: detected question, topic, status, source, and timestamps.
- `question_answers`: answer linkage, authority, confidence, and source.
- `claims`: grounded knowledge extracted from official answers/documents.
- `interactions`: bot answer, citations, latency, tools, and failure state.
- `user_facts`: scoped conversation memory.
- FTS5 indexes for messages, questions, claims, and official documents.

Question statuses:

- `OPEN`
- `BOT_ANSWERED`
- `STAFF_ANSWERED`
- `ESCALATED`

Both bot and staff answers count as resolved. Preserve:

- `resolution_source=BOT|STAFF`
- `staff_confirmed`
- `answer_message_id`
- `answer_source_timestamp`
- `source_snapshot_id`

If a later full reconciliation removes or changes the supporting answer, invalidate its claims and reopen affected questions.

Authority is determined from exact role IDs in the exported `author.roles` objects. Display names and role names are informational only.

Answer linkage order:

1. Explicit message reply/reference when present.
2. Staff response following a question in the same thread.
3. Thread-level semantic relation with confidence `>=0.80`.
4. Otherwise remain open.

Learner replies may be indexed as community context but cannot create official logistics claims.

## Assistant Interfaces

```python
@dataclass(frozen=True)
class AskRequest:
    user_id: str
    guild_id: str
    channel_id: str
    thread_id: str | None
    message_id: str
    text: str

@dataclass(frozen=True)
class Citation:
    source_type: Literal[
        "STAFF_DISCORD",
        "OFFICIAL_DOCUMENT",
        "TECHNICAL_WEB",
    ]
    title: str
    url: str
    excerpt: str
    authority: str
    source_timestamp: datetime | None

@dataclass(frozen=True)
class Answer:
    text: str
    intent: str
    confidence: float
    citations: list[Citation]
    status: str
    escalated: bool
    knowledge_freshness: datetime
    tools_used: list[str]

class Assistant:
    async def answer(self, request: AskRequest) -> Answer: ...
```

Discord, CLI, evaluation, and tests all use this same interface.

## LangGraph Workflow

1. Normalize and sanitize the request.
2. Load user-scoped memory.
3. Classify logistics, technical, ambiguous, out-of-scope, or conversational intent.
4. Retrieve program-server staff claims, official documents, FTS matches, and graph paths.
5. Apply authority, conflict, freshness, and confidence gates.
6. For technical questions only, optionally call Tavily.
7. Use Firecrawl only for selected Tavily result URLs.
8. Synthesize with Gemini at temperature `0`.
9. Verify that factual statements have citations.
10. Persist the interaction and question status.
11. Answer, clarify, refuse, or escalate.

Evidence precedence:

1. Program-server Admin/Lab Coach messages.
2. Official course/repository documents.
3. Technical web sources.
4. No evidence: clarify or escalate.

Tavily and Firecrawl must never establish deadlines, grading, submission, attendance, or course policy.

Do not send entire Discord exports to Gemini, Tavily, or Firecrawl. Send only the minimum retrieved excerpts after removing user identifiers. External web queries must be generalized and stripped of Discord names, IDs, and links.

Do not use a multi-agent swarm. One explicit LangGraph workflow is easier to audit, test, and explain to judges and maintainers.

## Bot and Staff Features

Student interfaces on the personal server:

- `/hoi`
- `!hoi`
- Direct bot mention
- Clarification prompts
- Citation links
- Visible knowledge freshness
- Explicit “not confirmed” behavior when evidence is stale or absent

Restricted operations:

- `/odyssey-status`
- `/odyssey-sync`
- `/odyssey-digest`
- `/odyssey-add-thread <numeric_id>`

These commands enqueue fixed operations. They do not expose a shell.

Daily digest includes:

- Latest successful program-server snapshot.
- Current exporter health.
- New questions in 24 hours.
- Open/escalated questions.
- Bot-answered but not staff-confirmed questions.
- Staff-answered questions.
- Repeated topics.
- Authority conflicts.
- Missing/deleted threads.
- Discovery-degraded warning.
- Direct source Discord links where available.

## Tool Policy

Reuse from Day 5:

- Gemini normalized response/tool-call adapter.
- Tavily result schema.
- Firecrawl page-reading schema.
- Shared structured error format.

Expose only these model tools:

- `search_internal_knowledge`
- `get_question_status`
- `search_technical_web`
- `read_technical_page`
- `escalate_question`

Do not expose:

- DiscordChatExporter.
- Shell execution.
- Thread discovery.
- Raw Discord search.
- Database writes.
- Knowledge-base mutation.
- Arbitrary HTTP fetch.
- Fake GitHub/VLearn operations.

## Configuration

Create `.env.example` with safe placeholders:

```text
DISCORD_BOT_TOKEN=
PERSONAL_DISCORD_GUILD_ID=
PERSONAL_DISCORD_STAFF_CHANNEL_ID=
PERSONAL_DISCORD_ADMIN_ROLE_IDS=

DCE_SYNC_ENABLED=false
DCE_USER_TOKEN=
DCE_SOURCE_GUILD_ID=
DCE_FORUM_CHANNEL_IDS=
DCE_STATIC_THREAD_MANIFEST=
DCE_EXPORTER_PATH=discord-chat-exporter-cli
DCE_DAILY_TIME=17:30
DCE_FULL_SYNC_DAY=sunday
DCE_FULL_SYNC_TIME=02:00
DCE_MAX_PARALLEL=2
DCE_TIMEOUT_SECONDS=1800

GEMINI_API_KEY=
AI_MODEL=
TAVILY_API_KEY=
FIRECRAWL_API_KEY=

DATABASE_PATH=data/runtime/odysseybot.sqlite3
DIGEST_TIME=18:00
TZ=Asia/Ho_Chi_Minh
DATA_RETENTION_DAYS=90
EXPORT_RETENTION_DAYS=7
LOG_LEVEL=INFO
```

Configuration validation must:

- Require separate bot and exporter tokens.
- Reject identical token values.
- Reject missing source guild/channel configuration when sync is enabled.
- Verify exporter version and executable availability.
- Never print secret values.
- Default exporter sync to disabled.

## Documentation

Create `docs/refactor/`:

- `README.md`: master plan, progress, decisions, and superseded docs.
- `architecture.md`: two-server topology, module interfaces, LangGraph, and trust zones.
- `source-ingestion.md`: exporter lifecycle, thread discovery, atomic imports, cursors, rate limits, failure recovery, and policy warning.
- `data-model.md`: SQLite schema, authority, question transitions, provenance, edits, and deletions.
- `stakeholders.md`: student, TA/Lab Coach, Admin, operator, developer, judge, and data-owner needs.
- `operations.md`: secrets, permissions, uv commands, systemd/container deployment, backups, rotation, and incident response.
- `evaluation.md`: test cases, golden-set policy, freshness targets, latency, and reporting.

Create a sanitized summary of the useful workflow from `session-ses_04f1.md`. Do not copy commands containing credentials. After token rotation and review, delete the raw session file from local storage or replace it with a redacted version.

## Implementation Sequence

1. Rotate the exposed Discord user token.
2. Create and publish `Thanh` from `4494746`.
3. Run the pre-refactor Graphify extraction.
4. Write the refactor documentation and source-ingestion threat model.
5. Establish the uv project and canonical `odysseybot` package.
6. Remove duplicate root source and broken compatibility wrappers.
7. Add SQLite migrations and import existing triples/Discord JSON.
8. Implement artifact validation and transactional imports.
9. Implement the isolated DCE subprocess adapter.
10. Seed and validate the existing thread manifest.
11. Implement capability probe, incremental sync, weekly full sync, and freshness reporting.
12. Implement authority detection and question-answer lifecycle.
13. Implement FTS5 retrieval and NetworkX projection.
14. Port Gemini, Tavily, and Firecrawl adapters.
15. Implement the grounded LangGraph workflow.
16. Implement personal-server bot commands and staff digest.
17. Replace keyword-only evaluation with structured assertions.
18. Update docs, regenerate Graphify, run all gates, and push to `origin/Thanh`.

Suggested commits:

1. `docs: define exporter-sidecar refactor architecture`
2. `build: establish uv project and canonical package`
3. `feat: add SQLite knowledge and question model`
4. `feat: add atomic Discord export importer`
5. `feat: add isolated scheduled exporter`
6. `feat: implement grounded LangGraph assistant`
7. `feat: add bot operations and daily digest`
8. `test: complete evaluation and operations documentation`

## Test Plan

Exporter tests:

- Token exists only in child environment.
- Token never appears in argv, logs, errors, manifests, or database.
- Agent cannot invoke exporter functions.
- Exporter path and arguments are fixed and validated.
- Invalid channel/thread IDs are rejected.
- Partial artifacts are never imported.
- Duplicate artifacts are idempotent.
- Invalid JSON/checksum/schema rejects the whole run.
- Cursor advances only after SQLite commit.
- `401`/`403` disables sync and alerts the operator.
- Repeated `429` opens the circuit breaker.
- Timeout kills only the exporter process group.
- Stale snapshot remains available after failed sync.
- Static manifest works when thread discovery is degraded.
- Weekly full sync detects edits and deletions.
- Digest declares stale or degraded data correctly.

Knowledge tests:

- Exported role IDs establish authority.
- Learner replies do not create official claims.
- Bot answers create `BOT_ANSWERED`.
- Staff answers create or upgrade to `STAFF_ANSWERED`.
- Removed source answers invalidate claims and reopen questions.
- Conflicting staff answers trigger review.
- FTS and graph retrieval preserve source links and timestamps.

Agent tests:

- Deadline/policy answers use only internal official evidence.
- Technical fallback may call Tavily and Firecrawl.
- Raw Discord content and identifiers never reach web tools.
- Every factual answer has valid citations.
- Missing/stale evidence clarifies or escalates.
- Tool and LLM failures degrade safely.
- Prompt injection cannot enable exporter/database/shell tools.

Acceptance gates:

- 100% deadline and official-policy cases correct and internally cited.
- At least 90% overall structured golden-set pass rate.
- Daily incremental import is idempotent.
- 18:00 digest always reports knowledge freshness.
- Internal retrieval p95 under five seconds.
- External technical fallback completes within fifteen seconds using deferred Discord responses.
- `uv sync`, Ruff, tests, coverage, evaluation, compile check, Graphify update, and `git diff --check` pass.
- No tokens, raw runtime exports, SQLite files, or user data are tracked by Git.

## Assumptions

- Branch `Thanh` must retain `4494746` as its branch point.
- The personal server can run a bot normally.
- Program-server access is performed through the selected isolated user-token job.
- The user accepts the account-security and Discord policy risk of unattended user-token automation.
- DiscordChatExporter `--include-threads All` will be probed but not assumed to work.
- The existing thread list seeds the fallback manifest.
- Program-server knowledge freshness is daily, not realtime.
- Personal-server interaction remains realtime.
- The deployment host provides persistent storage.
- Exported program data remains local, ignored, minimized, and never bulk-uploaded to external AI/search providers.
