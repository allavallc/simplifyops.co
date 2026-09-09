# Knowledge (human-maintained)

Curated, reviewed Markdown James can retrieve — read-only, authority-filtered. Super-admins edit via
`/admin/knowledge` (writes the database, not these files); these files are the initial seed + the
version-controlled source. Never put secrets here.

Every knowledge doc starts with front-matter:
`minimum_authority: contact|member|admin|super_admin` and `status: active|archived`.
Folders: principles, processes, patterns, playbooks, real-life-examples, case-studies, reference,
about-myself. See INDEX.md for the agent map.

`README.md`, `INDEX.md`, and `sources.md` are structural/human files — the seeder skips them.
