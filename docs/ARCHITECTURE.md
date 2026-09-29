# Architecture

ptcgl-linux is an unofficial Linux launcher and compatibility environment for
the official Windows build of Pokémon TCG Live.

The project does not reimplement Pokémon TCG Live.

## Design goals

- No manual Wine configuration.
- No requirement for Lutris or Bottles.
- No requirement for Steam.
- Isolated application-owned compatibility prefix.
- Managed and verified compatibility runtime.
- Native Linux browser authentication.
- Automatic `tpcitcgapp://` callback handling.
- No authentication credentials in logs.
- Repairable and diagnosable installation.
- Shared backend used by both the graphical desktop flow and CLI tools.

## Components

### Desktop application and CLI backend

The backend owns the installation and runtime logic used by both the graphical
desktop application and command-line tools.

Current commands:

- `ptcgl-linux install`
- `ptcgl-linux app`
- `ptcgl-linux play`
- `ptcgl-linux repair`
- `ptcgl-linux doctor`
- `ptcgl-linux uninstall`
- `ptcgl-linux callback <URI>`

Running the packaged Flatpak normally enters the same desktop application path
as `ptcgl-linux app`.

### Runtime manager

Responsible for:

- UMU installation and verification
- GE-Proton installation and version pinning
- Steam Linux Runtime management
- compatibility prefix creation
- runtime integrity checks

### Installer

Responsible for:

- obtaining the official Pokémon TCG Live installer
- validating that the download is an expected installer payload
- running installation inside the dedicated prefix
- discovering the installed game executable
- repair operations

### Launcher

Responsible for:

- starting Pokémon TCG Live
- maintaining known-good runtime environment variables
- capturing sanitized diagnostic output
- handling process lifetime

### Deep-link handler

Responsible for:

`x-scheme-handler/tpcitcgapp`

The callback URI is considered sensitive transient data.

It must be forwarded to the game and discarded without being persisted.

### Diagnostics

Responsible for reporting:

- supported architecture
- graphics stack
- Vulkan availability
- UMU/runtime versions
- Proton version
- prefix integrity
- game installation state
- URI handler state

## State locations

The application follows XDG conventions.

Primary application data:

`~/.local/share/ptcgl-linux/`

Configuration:

`~/.config/ptcgl-linux/`

Cache:

`~/.cache/ptcgl-linux/`

No runtime state belongs inside the Git repository.
