# ptcgl-linux

An unofficial Linux launcher and compatibility environment for the official
Windows version of Pokémon TCG Live.

> This project is not affiliated with, endorsed by, or sponsored by The Pokémon
> Company International, Nintendo, Creatures Inc., or GAME FREAK.

## Status

Early development.

A complete proof of concept has successfully run Pokémon TCG Live on Fedora 44
using UMU, GE-Proton, and the Steam Linux Runtime, including browser-based
Pokémon Trainer Central authentication and automatic `tpcitcgapp://` callback
handling.

See [docs/POC_BASELINE.md](docs/POC_BASELINE.md).

## Project goals

The intended user experience is:

1. Install ptcgl-linux.
2. Install Pokémon TCG Live.
3. Click Play.
4. Authenticate in the normal Linux browser.
5. Play.

Users should not need to manually configure Wine, Proton, Lutris, Bottles,
Winetricks, or URI handlers.

## Planned CLI

    ptcgl-linux install
    ptcgl-linux play
    ptcgl-linux repair
    ptcgl-linux doctor
    ptcgl-linux uninstall

The graphical launcher will use the same backend.

## Repository policy

This repository does not contain or redistribute:

- Pokémon TCG Live game files
- Pokémon artwork
- Pokémon credentials
- OAuth authorization codes or tokens
- Wine/Proton prefixes
- downloaded compatibility runtimes

## License

A project license has not yet been selected.
