# Proof-of-Concept Baseline

Verified: 2026-09-28

## Host

- Fedora Linux 44 Workstation
- x86_64
- AMD Radeon RX 580
- amdgpu kernel driver

## Compatibility stack

- UMU Launcher: 1.4.4
- UMU zipapp SHA-256:
  `eb590691841f7fad3fc3ad8fd5db4ccb87849fe7948e62b28ece7a4ee48cc851`
- GE-Proton: GE-Proton11-7-x86_64
- Steam Linux Runtime: steamrt4
- steamrt4 build tested: 4.0.20260914.260627
- Winetricks verb: vcrun2019
- GAMEID: 0

## Proven flow

The following sequence was successfully tested end-to-end:

1. UMU downloaded and verified GE-Proton.
2. UMU downloaded and verified steamrt4.
3. A dedicated Wine/Proton prefix was created.
4. vcrun2019 was installed.
5. The official Pokémon TCG Live Windows MSI was installed.
6. Pokémon TCG Live launched successfully.
7. Rendering worked on the RX 580.
8. The game launched the native Linux web browser for authentication.
9. Linux registered an `x-scheme-handler/tpcitcgapp` URI handler.
10. Pokémon Trainer Central returned a `tpcitcgapp://callback?...` URI.
11. The Linux URI handler forwarded the callback to the game using the same
    prefix and Proton environment.
12. Pokémon TCG Live completed authentication and reached the user's account.
13. Authentication persisted across a full game restart.

## Callback behavior

The PoC used:

- `PROTON_VERB=runinprefix`
- `UMU_CONTAINER_NSENTER=1`

UMU attempted container namespace re-entry but did not locate the expected
D-Bus application name after five retries. It then fell back to a normal
launch against the existing prefix.

That fallback successfully delivered the callback to Pokémon TCG Live.

The production launcher must therefore not depend on successful namespace
re-entry unless this behavior is separately verified.

## Security finding

The initial experimental callback script logged the full OAuth callback URL.

That is not acceptable production behavior.

Production requirements:

- Never log OAuth authorization codes.
- Never log OAuth state values.
- Never log the full `tpcitcgapp://` callback URI.
- Authentication logs may record only that a callback was received and whether
  processing succeeded.
- Runtime logs and state files must use user-private permissions where
  appropriate.

## Known-good executable location in PoC prefix

`C:\users\steamuser\The Pokémon Company International\Pokémon Trading Card Game Live\Pokemon TCG Live.exe`

The production launcher must discover or validate this path rather than assume
it blindly.
