# Sample: Windows Debugging (WinDbg) Notes

Tiny demo notes for testing the assistant. Replace with your real debugging notes later.

## First commands on a crash dump
1. `!analyze -v` — runs the automated bugcheck analysis and prints the probable cause,
   faulting module, and stack.
2. `lm` — list loaded modules (use `lm v m <name>` for version detail).
3. `k` — display the call stack of the current thread.

## Bugcheck 0x9F (DRIVER_POWER_STATE_FAILURE)
Occurs when a driver fails to complete a power IRP within the allotted time, commonly
during sleep/resume. Look at parameter 1 to identify the blocked power transition. Use
`!devstack` and `!irp <address>` to find the driver holding the IRP. The offending driver
is frequently a storage, network, or USB filter driver.

## Bugcheck 0xD1 (DRIVER_IRQL_NOT_LESS_OR_EQUAL)
A driver accessed pageable memory at too high an IRQL. Parameter 1 is the referenced
address, parameter 4 is the instruction that referenced it. `!analyze -v` usually names the
faulting driver; confirm with `lm` and check for an updated version.

## Symbols
Set the symbol path to the Microsoft public store for readable stacks:
`.sympath srv*C:\symbols*https://msdl.microsoft.com/download/symbols` then `.reload`.
