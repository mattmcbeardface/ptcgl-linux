# PTCGL-Linux

PTCGL-Linux is an unofficial Linux compatibility package for the official
Windows version of Pokémon TCG Live.

Website: https://ptcgl-linux.com

> This project is not affiliated with, endorsed by, or sponsored by The Pokémon
> Company International, Nintendo, Creatures Inc., or GAME FREAK.

## Install

Download the Flatpak from:

https://ptcgl-linux.com

The normal installation flow is:

1. Download the Flatpak installer from the website.
2. Install Pokémon TCG Live through the Linux software installer.
3. Launch Pokémon TCG Live from the application menu.
4. On first launch, PTCGL-Linux prepares the compatibility environment and
   installs the official game client.
5. Authenticate through the normal browser when prompted.
6. Later launches start the game directly.

No manual Wine, Proton, Winetricks, Lutris, Bottles, Steam, or URI-handler
configuration is required.

## Compatibility stack

The current package uses:

- Flatpak
- UMU Launcher
- GE-Proton
- Steam Linux Runtime
- an application-owned Proton prefix

The official Pokémon TCG Live installer is downloaded and verified at first
setup. Pokémon TCG Live itself is not distributed by this project.

## Command-line tools

The graphical desktop application is the normal user interface.

Diagnostic and maintenance commands are also available:

```text
ptcgl-linux install
ptcgl-linux app
ptcgl-linux play
ptcgl-linux repair
ptcgl-linux doctor
ptcgl-linux uninstall
ptcgl-linux callback <URI>
```

Running `ptcgl-linux` without a subcommand launches the desktop application.

## Authentication

PTCGL-Linux integrates the official browser-based login flow with Linux using
the `tpcitcgapp://` URI scheme.

Authentication callback URLs, authorization codes, state values, credentials,
and tokens must never be logged or persisted by PTCGL-Linux.

## Repository policy

This repository does not contain or redistribute:

- Pokémon TCG Live game files
- Pokémon credentials
- OAuth authorization codes or tokens
- Wine/Proton prefixes
- downloaded compatibility runtimes

## Development

Run the test suite with:

```bash
.venv/bin/python -m unittest discover -s tests -v
```

The Flatpak manifest is:

```text
packaging/flatpak/io.github.PTCGLLinux.yml
```

The application ID is:

```text
io.github.PTCGLLinux
```

## License

PTCGL-Linux is licensed under the MIT License. See `LICENSE`.
