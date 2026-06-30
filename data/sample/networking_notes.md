# Sample: Windows Networking Notes

These are tiny demo notes committed to the repo so the pipeline can be tested end-to-end
before you point it at your real corpus. Replace/remove them once your own notes are in
`data/corpus/`.

## Winsock reset
`netsh winsock reset` restores the Winsock catalog to a clean state. Use it when network
connectivity is broken after malware removal or a misbehaving LSP (layered service
provider) injects itself into the stack. A reboot is required afterward.

## Flushing DNS
`ipconfig /flushdns` clears the local DNS resolver cache. Symptoms that suggest a stale
cache: a site resolving to an old IP, or intermittent name resolution failures after a DNS
record change. `ipconfig /displaydns` shows the current cache.

## TCP RST vs FIN
A FIN indicates a graceful connection close (the four-way handshake). A RST is an abrupt
reset — often a sign that a port is closed, a firewall dropped the flow, or an application
crashed. Frequent RSTs in a capture point to mid-connection failures rather than normal
teardown.

## Useful commands
- `netstat -ano` — list connections with owning PID.
- `Get-NetTCPConnection` — PowerShell equivalent with richer filtering.
- `pathping <host>` — combines ping and tracert to locate packet loss per hop.
