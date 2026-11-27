# Networka

Networka is a multi-vendor device automation CLI and Python library whose `nw test` part is the test engine for containerlab labs.
Each lab lives in its own **lab repository** and holds only its description; Networka holds everything that runs and judges a test.

## Language

### Devices and inventory

**Device**:
A network device or Linux system in the **inventory** that Networka reaches by name.
_Avoid_: host (for a device), node (outside a **lab**), box

**Inventory**:
The **devices** and **groups** Networka knows by name, with each device's **platform** and access details.
_Avoid_: device list, hosts file

**Group**:
A named set of **devices** in the **inventory**, given by its members, by tag or by both.
_Avoid_: site, role (for a group)

**Platform**:
The network operating system of a **device**, which selects how Networka talks to it, which **sequences** apply and which **readers** read its state.
_Avoid_: vendor, driver, device type (in prose)

**Sequence**:
A named list of commands that Networka runs on a **device**, chosen by its name and the device's **platform**.
_Avoid_: script, command set, playbook

**Session**:
One open connection to a **device**, reused for every command to that device.
_Avoid_: login, connection (for this)

**Saved output**:
The output of one command on one **device**, saved earlier, that `nw diff` compares with the output of the same command now.
_Avoid_: baseline (for saved output), golden copy, snapshot

### Intent

**Intent file**:
A list of **items** that states the device state a network should be in, with exact expected values and no operators.
_Avoid_: spec, policy, assertion file

**Item**:
One entry of an **intent file**: one **check** on one **device** with its expected value.
_Avoid_: assertion, rule, test (for an item)

**Check**:
A named comparison of one kind of device state with its expected value, such as the MLAG state of a bridge or the flags of one LACP member; a neutral check applies to every **platform** that has a **normalizer** for it, and other checks belong to one platform.
_Avoid_: test (for a check), assertion, probe

**Reply**:
What a **device** returned for one command.
_Avoid_: response, observation, raw output

**Reader**:
The part of a **platform** that sends the commands for one kind of device state and saves their **replies** as a **reading**, without judging them.
_Avoid_: collector (for this), poller, getter

**Reading**:
The **replies** of one **reader** on one **device** at one moment.
_Avoid_: snapshot, sample

**Normalizer**:
The part of a **platform** that turns **replies** into the fields a **check** compares.
_Avoid_: parser, translator, mapper

### Labs

**Lab**:
One containerlab topology of switches, **hosts** and, when it keeps switch logs, a **collector**, with the configuration its **nodes** boot with, its **lab file** and its **tests**.
_Avoid_: setup, environment, scenario, testbed

**Lab file**:
The file that describes a **lab** to Networka: its **streams**, its **state checks** and where the **collector** keeps the switch log.
_Avoid_: lab config, topology (for this)

**Node**:
One container of a deployed **lab**, such as a switch, a **host** or the **collector**.
_Avoid_: container, VM, device (for a lab node)

**Host**:
A Linux **node** of a **lab** that sends and answers the **pings** of the **streams**.
_Avoid_: client, endpoint, end system, probe host

**Lab repository**:
A repository that holds one or more **labs**, their **tests** and their **limits**, and no test logic.
_Avoid_: test suite (for the repository), lab project

**Lab machine**:
The Linux machine that runs the containers of a **lab** and on which Networka runs its **tests**.
_Avoid_: lab host, Docker host, host (for the machine)

**Point**:
One interface of a **node**, written node:interface, where a **stream** starts or ends or where Networka captures packets.
_Avoid_: endpoint, port (for a point), tap

**Cable**:
The virtual wire between two **points** that a **step** takes down or brings back.
_Avoid_: link (for the wire), connection, carrier withdrawal

**Collector**:
The **node** that receives the log of every switch in a **lab**, so the log is kept with every **run** even while data links are down.
_Avoid_: log server, syslog server, receiver

**Marker**:
A log line that every switch sends at the start and at the end of a **run** on Networka's request, which proves the **collector** received that switch's whole log for the run.
_Avoid_: beacon, sentinel

### Tests

**Test**:
One named, ordered list of **steps** run on one **lab**, kept in one test file, with a descriptive name such as primary-reboot.
_Avoid_: case, test case, case intent, use case, scenario

**Step**:
One stretch of a **test** with one **action**, its **hold**, its **limits** and the expected behaviour.
_Avoid_: phase, stage

**Action**:
What one **step** does to the **lab**: a **cable** change, a **reboot**, the start or end of a **power loss** or a **traffic fault**, a change of the active member of a host's active-backup bond, or nothing but observing.
_Avoid_: operation, command (for this), event

**Hold**:
The time a **step** keeps measuring after its **action**, and after the **state checks** pass again when the action needs them to.
_Avoid_: wait, dwell, sleep

**Recovery deadline**:
The longest time a **step** allows after a **reboot** or the end of a **power loss** for every **state check** to pass again.
_Avoid_: wait healthy, health timeout, boot timeout

**Fault**:
The event a **test** injects to see how the network copes, such as a **reboot**, a **power loss**, a **cable** going down or a **traffic fault**; it is down while in effect and back when it ends.
_Avoid_: scenario, failure, withdrawal and restoration, lost and restored, loss and return

**Traffic fault**:
A **fault** that changes what a **cable** carries without taking it down, such as an **impairment**, dropping the **pings** of one **stream**, silencing LACP or silencing a host's active-backup bond.
_Avoid_: fault (for these alone), filter fault

**Impairment**:
Packet loss, delay or both, added to the traffic that leaves one **point**.
_Avoid_: netem (in prose), degradation, shaping

**Reboot**:
A restart of one switch's operating system from its own command, during which its data links may keep carrier.
_Avoid_: soft reboot, hardware failure, power loss

**Power loss**:
One or more **nodes** switched off abruptly, with carrier gone on all their data links, and left off for a set time before they boot again.
_Avoid_: reboot, hard reboot, pause, sustained stop

**Baseline**:
Fault-free traffic with a **limit** of 0 on every **stream**, as a **test** of its own that proves the **lab** forwards or as the opening **step** of a test.
_Avoid_: readiness, readiness gate, zero-loss gate, old results, saved output

**State check**:
A set of **checks** of device state, named by the **lab file** or a **step**, that runs before a **test**, again at its end, and after a **reboot** or **power loss** before measuring goes on.
_Avoid_: statement, checkpoint, snapshot, gate, readiness, precondition, health check, health

**Log rule**:
A text that the log of one switch, or of every switch, must or must not contain during a **test** or one **step**.
_Avoid_: log check, log assertion, pattern

**Flood check**:
A check of a **test** that broadcast and unknown-unicast frames sent from a host's LACP bond never return to that host.
_Avoid_: flood probe, loop check

**Host-entry watch**:
Regular sampling of chosen bridge host entries on chosen switches during the **steps**, where every watched entry must stay present.
_Avoid_: MAC watch, FDB poll

### Measurement

**Stream**:
One series of **pings** in one direction from one **point** to another point or to a fixed address, named by its direction, such as host1-to-host2.
_Avoid_: flow, graded flow, control flow, stream 101

**Ping**:
One numbered ICMP echo of a **stream**.
_Avoid_: probe, packet

**Lost ping**:
A **ping** whose reply did not arrive in time.
_Avoid_: drop, packet loss (for pings)

**Outage**:
The measured interruption of one **stream**: consecutive **lost pings**, given as a lower and an upper bound, such as 24 lost pings at one every 100 ms, an outage of 2.4 to 2.6 s.
_Avoid_: stop (as a noun), gap, convergence time, withdrawal bound, restoration bound

**Limit**:
The longest **outage** a **stream** may have in a **step**, written with its reason and source; 0 means no **lost ping**.
_Avoid_: loss limit, timer, threshold, target, SLA

**Quiet window**:
The stretch of clean traffic on every **stream** that must come before the first **action** of a **test**.
_Avoid_: baseline (for this window), pre-fault window, settle time

**Closing window**:
The stretch of traffic from the end of the last **hold** through the final **state check**, which must be as clean as the **quiet window**.
_Avoid_: tail, post-test window

**Validity check**:
A check that the measurement itself is sound, such as a steady sending pace, no dropped captures and a clean **quiet window**; a failed validity check gives ERROR, not FAIL.
_Avoid_: calibration, sanity check, bypass

### Results

**Run**:
One execution of one **test** on a live **lab**, or of one **intent file** on its **devices**, saved with its **evidence**.
_Avoid_: attempt, trial, repeat

**Evidence**:
What a **run** keeps for its **verdict**: the packet captures the **judge** needs, the **replies** of every **state check** or **item**, the timed **actions** and the switch log.
_Avoid_: proof, archive, recordings

**Judge**:
The part of **Networka** that turns **evidence**, **limits** and **state checks** into a **verdict**; plain code, not an AI.
_Avoid_: grader, evaluator, scorer, grading

**Verdict**:
The result of a **check**, **step**, **run** or **test**, written in capitals as PASS, FAIL or ERROR. ERROR means the **evidence** cannot decide, and missing evidence is never PASS.
_Avoid_: unverified, not available, INVALID, inconclusive, unavailable, finding (for a FAIL)

**Replay**:
Judging the saved **evidence** of a **run** again without the **lab** or the **devices**; it must give the same result and **report** byte for byte.
_Avoid_: offline, re-grade, verify, re-run

**Report**:
The generated account of a **run**: the **verdict** first, then per **step** and **stream** the expected **limit** against the measured **outage**; nothing in it is written by hand.
_Avoid_: timeline, write-up

**Networka**:
A multi-vendor device automation CLI and Python library whose `nw test` part is the test engine that runs and judges every **test** of a **lab repository**.
_Avoid_: runner, Containerlab tests, toolkit

## Relationships

- An **intent file** has **items**; each **item** names one **check** on one **device**, and the **readers** and **normalizers** of the device's **platform** give that check its fields.
- A **lab** has one **lab file**, when it keeps switch logs one **collector**, several **streams** and many **tests**; a **node** that Networka checks is also a **device** in the **inventory**.
- A **test** has ordered **steps**; each **step** has one **action** and one **limit** per **stream**.
- A **fault** is down in one **step** and back in a later one; each **step** measures its own **outages**.
- A **run** of a **test** produces **evidence**; the **judge** turns it into one **verdict** and a **report**; a **replay** repeats that from the **evidence** alone.

## Flagged ambiguities

- Host: "host" was used for a Linux lab node ("a dual-connected host"), for the machine that runs the lab's containers ("the Linux host running its Docker containers") and for a device address in the inventory. Resolved: **host** is the Linux lab node, the machine is the **lab machine**, and an inventory entry is a **device**.
- Baseline: "baseline" was used for fault-free traffic with a 0 s limit, for the file `nw diff` compares against, and for the clean traffic before the first action. Resolved: **baseline** is fault-free traffic, the file is **saved output**, the traffic before the first action is the **quiet window**.
- Fault: "fault" was used for every injected event, including reboot and power loss, and also for loss, delay and filters alone ("a traffic fault or power restoration"). Resolved: **fault** is every injected event; loss, delay and filters are **traffic faults**.
- Collector: "collector" was used for the syslog node of a lab and for the platform code that reads and saves device replies. Resolved: **collector** is the syslog node; the platform code is a **reader**.
- Check: "check" was used for one intent comparison, for the device state a test checks before and after, for the soundness of a measurement and for log rules. Resolved: a **check** is one comparison; a **state check** is a set of them named by the lab file or a step; a **validity check** judges the measurement; a **log rule** judges the switch log.
