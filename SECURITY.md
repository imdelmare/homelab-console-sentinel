# Security policy

## Boundary

Sentinel is an availability observer only. Runtime callers cannot provide URLs,
commands or remediation targets. It has no Homelab Console database, MCP token,
provider credentials, Docker socket or infrastructure write path.

Heartbeat authentication fails closed when the configured token is missing or
invalid. Store the heartbeat token and Telegram credentials only in local runtime
configuration. Never include them in issues, logs, images or source control.

Bind the listener to loopback or a private network. If heartbeats cross an
untrusted network, terminate TLS in a controlled proxy and rotate the bearer
token after suspected disclosure.

## Reporting

Report vulnerabilities through GitHub private vulnerability reporting for this
repository. Do not open a public issue containing credentials, private network
details or an undisclosed exploit.

Supported security fixes target the latest v1 release. Breaking protocol changes
require a new contract major version.
