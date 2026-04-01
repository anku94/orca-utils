# ORCA Umbrella Build System

Umbrella is a CMake-based build system that downloads, builds, and installs the full dependency tree for ORCA. Each package gets a `.cmake` module that specifies how to fetch and build it, and the root `CMakeLists.txt` selects which packages to enable.

## How It Works

1. Each package has a module in `umbrella/umbrella/<package>.cmake`
2. The root `CMakeLists.txt` includes the modules you want to build
3. Run `make -jN` from the `build/` directory
4. Everything installs to a shared prefix (e.g., `ou-install/`)

Dependencies are handled automatically — each module declares `DEPENDS` on other modules, and `include(umbrella/<dep>)` pulls in transitive deps.

## Module Conventions

Two patterns for `.cmake` modules:
- **Git**: `REPO` + `TAG`, downloads via git clone
- **Tarball**: `BASEURL` + `URLFILE` + `URLMD5`, downloads release archive

Both use: `if (NOT TARGET ...)` guard, `umbrella_defineopt`, `umbrella_download`, `umbrella_patchcheck`, `ExternalProject_Add` with DEPENDS/CMAKE_ARGS.

## Root CMakeLists.txt Rules

- **Never delete lines** from the root CMakeLists.txt. Comment out includes you don't need right now. The file is the configuration surface for the whole tree — option defaults (e.g., `BOOST_WITHLIBS`) are shared across consumers and may need tuning as new packages are added.
- To enable a package: uncomment its `include(umbrella/<package>)` line
- To disable: comment it out

## Workflow

### Adding a new package to the build
1. Ensure a `.cmake` module exists in `umbrella/umbrella/<package>.cmake`
2. Add (or uncomment) `include(umbrella/<package>)` in the root `CMakeLists.txt`
3. Run `make -jN` from the `build/` directory — it will download and build the new package and any missing dependencies

### Rebuilding after changes
- Just run `make -jN` from `build/`. CMake will detect changes to the root `CMakeLists.txt` and reconfigure automatically.
- No need to delete the build tree — existing packages are cached.

### Checking what's enabled
- `orca-umbrella/CMakeLists.txt` — what's currently included
- `orca-umbrella/umbrella/umbrella/*.cmake` — available modules and per-package details

## Build Notes

### make
- On some systems (e.g., zsh), `make` may be shadowed by an autoload. Use `/usr/bin/make` explicitly.

### Install prefix
- Default install prefix is set by `-DCMAKE_INSTALL_PREFIX` at initial configure time
- All packages install to this shared prefix, so consumers can use `-DCMAKE_PREFIX_PATH=<prefix>` to find them
