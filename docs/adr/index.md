# Architecture decisions

These records say why Networka is shaped as it is. Each one states the decision, the context that led to it and its consequences.

- [0001: Networka holds all test logic, and a lab is only a description](0001-networka-holds-all-test-logic-and-a-lab-is-only-a-description.md)
- [0002: A test is a YAML file of exact values, and running it needs no AI](0002-a-test-is-a-yaml-file-of-exact-values-and-running-it-needs-no-ai.md)
- [0003: A lab test pushes no configuration, and state checks prove the lab state](0003-a-lab-test-pushes-no-configuration-and-state-checks-prove-the-lab-state.md)
- [0004: Lab actions run on containerlab only](0004-lab-actions-run-on-containerlab-only.md)
- [0005: Outage is measured from numbered pings every 100 ms, captured at both ends](0005-outage-is-measured-from-numbered-pings-every-100-ms-captured-at-both-ends.md)
- [0006: Replay judges saved evidence again and must give a byte-identical result](0006-replay-judges-saved-evidence-again-and-must-give-a-byte-identical-result.md)
- [0007: The run writes its report, and nobody writes verdicts or numbers by hand](0007-the-run-writes-its-report-and-nobody-writes-verdicts-or-numbers-by-hand.md)
- [0008: A run keeps only the capture slices that prove its verdict](0008-a-run-keeps-only-the-capture-slices-that-prove-its-verdict.md)
- [0009: Switch logs come from one collector, and markers prove they are complete](0009-switch-logs-come-from-one-collector-and-markers-prove-they-are-complete.md)
- [0010: Networka reaches every lab node over SSH at the address containerlab assigned](0010-networka-reaches-every-lab-node-over-ssh-at-the-address-containerlab-assigned.md)
- [0011: A reboot is the switch's own reboot, and a power loss pauses the guest and withdraws carrier](0011-a-reboot-is-the-switch-s-own-reboot-and-a-power-loss-pauses-the-guest-and-withdraws-carrier.md)
- [0012: Validity checks prove the measurement](0012-validity-checks-prove-the-measurement.md)
- [0013: Device state is read as the device's own JSON, not parsed from text](0013-device-state-is-read-as-the-device-s-own-json-not-parsed-from-text.md)
- [0014: A check has three verdicts, and missing evidence never passes](0014-a-check-has-three-verdicts-and-missing-evidence-never-passes.md)
- [0015: A test keeps one SSH session per device](0015-a-test-keeps-one-ssh-session-per-device.md)
- [0016: Impairments use tc netem in the node's namespace](0016-impairments-use-tc-netem-in-the-node-s-namespace.md)
- [0017: Networka uses Scrapli 2 and takes the platform from the inventory, without autodetection](0017-networka-uses-scrapli-2-and-takes-the-platform-from-the-inventory-without-autodetection.md)
- [0018: Networka keeps its own runtime and does not adopt Nornir](0018-networka-keeps-its-own-runtime-and-does-not-adopt-nornir.md)
- [0019: The Textual TUI is retired](0019-the-textual-tui-is-retired.md)
- [0020: Networka requires the latest stable Python and uses uv for all Python work](0020-networka-requires-the-latest-stable-python-and-uses-uv-for-all-python-work.md)
