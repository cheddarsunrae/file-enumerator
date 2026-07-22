# Installation

## Fedora and other Linux systems

Requirements:

- Python 3.9 or newer
- GNU Make and standard Unix installation tools
- `man-db` for indexed manual-page lookup
- `bash-completion` for Bash completion

On Fedora:

```bash
sudo dnf install python3 make man-db bash-completion
```

Install system-wide under `/usr/local`:

```bash
./scripts/install.sh
hash -r
file-enumerator --version
man file-enumerator
```

The installer runs `sudo make install` when root privileges are required. It
installs only these files:

```text
/usr/local/bin/file-enumerator
/usr/local/share/man/man1/file-enumerator.1
/usr/local/share/bash-completion/completions/file-enumerator
```

Uninstall:

```bash
./scripts/uninstall.sh
```

## Per-user installation

No root access is required:

```bash
PREFIX="$HOME/.local" ./scripts/install.sh
```

Ensure these paths are available in the shell environment:

```bash
export PATH="$HOME/.local/bin:$PATH"
export MANPATH="$HOME/.local/share/man:${MANPATH:-}"
```

Uninstall the per-user copy:

```bash
PREFIX="$HOME/.local" ./scripts/uninstall.sh
```

## Fedora RPM build

Install the RPM build tools:

```bash
sudo dnf install rpm-build rpmdevtools python3 make bash-completion
```

Build and stage the source archive:

```bash
make dist
rpmdev-setuptree
cp dist/file-enumerator-1.1.1.tar.gz ~/rpmbuild/SOURCES/
cp packaging/rpm/file-enumerator.spec ~/rpmbuild/SPECS/
rpmbuild -ba ~/rpmbuild/SPECS/file-enumerator.spec
```

Install the resulting noarch RPM from `~/rpmbuild/RPMS/noarch/` with `dnf`.

## Validation and rollback

Before installation:

```bash
make verify
```

To test installation without touching the live filesystem:

```bash
STAGE="$(mktemp -d)"
make install DESTDIR="$STAGE" PREFIX=/usr/local
find "$STAGE" -type f -print
rm -rf "$STAGE"
```

Rollback is `make uninstall` or `scripts/uninstall.sh`; no configuration files,
databases, services, or shell startup files are modified.


## Publish the public GitHub repository

The repository includes a guarded publication script. It requires an installed
and authenticated GitHub CLI:

```bash
gh auth status
./scripts/publish-github.sh
```

By default it targets `cheddarsunrae/file-enumerator`, requires branch `main`,
and creates the repository as public. It stops rather than changing an
unexpected `origin`, publishing a dirty tree, or using an existing non-public
repository.
