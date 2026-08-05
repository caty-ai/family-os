# Security Policy

Family OS is a documentation repository. It ships no executable code, installs nothing, runs no daemon, and opens no network ports. Its security surface is what it points people toward and what it might accidentally carry. Security reports are welcome for:

- Leaked credentials, tokens, or personal information anywhere in the repository or its git history
- Links in the documentation that point to malicious, hijacked, or otherwise compromised destinations
- A described practice that would lead a reader to expose credentials, weaken an isolation boundary, or grant an agent authority the document does not intend
- A module described here in a way that materially understates what it can reach or change

Vulnerabilities inside a module itself (Caty Agent Harness, Persona Engine, Sitter, and others) belong to that module's own repository and security policy. If you are unsure, report it here and we will route it.

## Reporting a Vulnerability

Please report security issues privately via **GitHub's private vulnerability reporting** on this repository (Security → Report a vulnerability). If that is unavailable, open a GitHub issue *without sensitive details* and ask a maintainer to establish a private channel.

We aim to acknowledge reports within 7 days. Please do not disclose the issue publicly until it has been addressed.

## Supported Versions

Only the `main` branch is maintained.
