# Security Policy

## Supported Versions

Security fixes are applied to the latest revision of the default branch. Older tags, forks, local upstream mirrors, and generated catalogs are not supported release lines.

## Report a Vulnerability

Do not open a public issue for a suspected vulnerability. Use GitHub's **Security** tab and select **Report a vulnerability** to submit a private security advisory for this repository. If private vulnerability reporting is unavailable, contact the repository owner through the private contact method listed on the owner's GitHub profile and ask for a secure reporting channel; do not send exploit details in the initial message.

Include, when safe:

- affected revision and component;
- impact and required attacker capabilities;
- minimal reproduction using non-sensitive data;
- whether the issue crosses the reviewed-core boundary, enables writes, escapes repository paths, leaks credentials, or executes upstream content;
- suggested mitigation, if known.

Do not include real credentials, private skill content, customer data, or destructive proof-of-concept payloads.

## Response Targets

Maintainers aim to acknowledge a report within 3 business days, provide an initial assessment within 7 business days, and send progress updates at least every 14 days until resolution. These are targets, not a guarantee. Severity, fix timing, disclosure date, and credit will be coordinated with the reporter.

Please allow a reasonable remediation window before disclosure. Maintainers will request a CVE when appropriate and publish remediation guidance after a fix is available.

## Scope

In scope includes path traversal, unsafe file writes, command execution, dependency compromise, MCP trust-boundary bypass, secret disclosure, denial of service, and promotion or execution of unreviewed upstream/young skills. Vulnerabilities in an upstream repository should normally be reported to that upstream project unless this library's handling makes them exploitable here.

Social engineering, availability attacks against third-party services, and reports based only on an untrusted upstream skill containing unsafe prose are out of scope unless the default runtime executes or returns that content contrary to policy.

## Operator Guidance

Run the MCP server without `--allow-writes` for production clients, use `uv sync --frozen`, pin and review upstream revisions, protect repository write access, and keep generated reports private until inspected. Streamable HTTP must remain bound to loopback; expose it remotely only through an SSH tunnel or same-host TLS/authenticating reverse proxy with a request-body limit. Use `--auth-token-env` for the built-in controlled-environment Bearer gate, never put the token in argv or tracked files, and do not describe that gate as OAuth. See [the charter](docs/skill-control-plane-charter.md) and [agent operations](docs/agent-usage.md#operations).
