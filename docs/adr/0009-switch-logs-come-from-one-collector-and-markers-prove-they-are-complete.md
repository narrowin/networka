# Switch logs come from one collector, and markers prove they are complete

A lab that has switch logs sends them to one collector node on its management network, and the lab file names the collector's file.
Networka records where the file stands, has every switch send a start marker over its session, and after the last step has every switch send an end marker.
It saves the lines between the markers as `syslog.log` with the run and judges the log rules against them.
A switch whose markers did not arrive makes the log rules ERROR, and a stopped collector fails the run before it starts.

## Why

On 2026-11-26 the first clean MLAG build dropped its collector because no test read it.
The operator reversed that the same day: "Where do you actually keep the syslog output of all the devices? It's also important."
The device logs are the evidence a person needs to understand a failure.
The collector sits on the management network, so it keeps receiving from the surviving switches while the data plane is broken.
One collector gives one ordered file, timed by one clock, instead of a log read from each switch after the run.
Without markers an empty log could mean a silent switch or a collector that lost its messages.

## Consequences

A lab needs an extra node and a management address that every switch's configuration names.
A sender the collector does not recognise also invalidates the log coverage.
