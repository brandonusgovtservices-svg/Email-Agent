# Agents

Persona-based subagent definitions for Claude Code, sourced from
[The Agency](https://github.com/msitarzewski/agency-agents) (MIT licensed)
and selected for relevance to this project and to US government-services
contracting work.

| File | Use for |
|------|---------|
| `engineering-email-intelligence-engineer.md` | Extending this repo's Gmail/MIME parsing and reply-drafting pipeline |
| `government-digital-presales-consultant.md` | Federal/gov digital transformation proposals and bids |
| `specialized-fedramp-rmf-compliance.md` | FedRAMP / NIST 800-53 authorization work (SSP, POA&M, ConMon) |
| `engineering-section-508-specialist.md` | Section 508 / WCAG accessibility review and remediation |
| `engineering-uswds-developer.md` | US Web Design System components and patterns |
| `customer-service.md` | Client-facing support and complaint-handling replies |
| `marketing-email-strategist.md` | Lifecycle/outreach email strategy and deliverability |
| `engineering-git-workflow-master.md` | Branching strategy, commit hygiene, history cleanup |
| `engineering-code-reviewer.md` | PR review, code quality gates |

To use one, invoke it by name, e.g. "Activate Email Intelligence Engineer and help me restructure `tools/gmail.py`'s thread parsing."

More agents are available in the full roster at
https://github.com/msitarzewski/agency-agents — install via its
`scripts/install.sh --tool claude-code` or copy additional `.md` files
into this directory the same way.
