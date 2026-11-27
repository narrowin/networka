# Networka uses Scrapli 2 and takes the platform from the inventory, without autodetection

Networka runs device CLI sessions only through Scrapli 2, the `scrapli==2026.11.12` distribution that reports version 2.0.4, and it was released straight as 0.2.0 on that driver.
The legacy Scrapli driver is gone.
A device's platform comes from its inventory entry or from `--platform` for an IP target; Networka does not query a device to guess it.

## Why

On 2026-11-24 the operator chose the full switch over a candidate that kept both drivers: "Let's go with Scrapli 2 then."
He also asked why it should go out as a release candidate first, since there was no separate group of users to test one, and 0.2.0 was released directly the same day.
On 2026-11-25 he asked to check whether Scrapli has platform detection, so that Networka could use it instead of a fixed mapping.
Scrapli 2.0.4 selects its `default` definition when no name is given, honours an exact name and rejects an unknown one; it has no detection API.

## Considered options

- **Keep the legacy Scrapli driver beside Scrapli 2.** Rejected: two drivers for a tool with few users.
- **A 0.2.0rc1 pre-release.** Rejected for the reason above.
- **A probing layer of Networka's own that guesses the platform.** Rejected: Scrapli offers none, and a wrong guess would pick wrong commands silently.

## Consequences

An IP target without a platform gets an error that names the platform option.
A new platform needs only a Scrapli definition and, for intent checks, its readers and normalizers.
