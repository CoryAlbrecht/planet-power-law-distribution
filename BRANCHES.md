# Repository Branching & Release SOP

## Initial Setup (One-Time)

Before the automation works, the "brain" must be in the master branch.

### Step A: Create the Workflow File

On the master branch, create .github/workflows/release-manager.yaml and paste the unified code from the previous message.

### Step B: The "Surgery" (Seeding the branches)

Run these commands to ensure the old branches have the new instructions without merging the rest of `master` into them.Bash# Update version-0.1.0

```sh
# Update version-0.1.0
git checkout version-0.1.0
git checkout master -- .github/workflows/release-manager.yaml
git commit -m "docs: add release automation SOP"
git push origin version-0.1.0


# Update version-0.2.0
git checkout version-0.2.0
git checkout master -- .github/workflows/release-manager.yaml
git commit -m "docs: add release automation SOP"
git push origin version-0.2.0
```

## Team SOP: Working with Versions

Provide this guide to your team. It assumes they are working in a Unix-like terminal.

### Case A: Starting a New Development Cycle (e.g., v0.3.0)

When moving from $0.2.0$ to $0.3.0$:

1. **Create the branch:**

```sh
git checkout -b version-0.3.0 master
```

1. **Set the "Unstable" flag:**

Open `pyproject.toml`.

Locate the line: `version = "0.2.0"`.

Change it to: version = `"0.3.0-dev"`.

Change `__version__` in `__init__.py` to match.

1. **Push to GitHub:**

```sh
git add pyproject.toml
git commit -m "chore: bump version to 0.3.0-dev"
git push -u origin version-0.3.0
```

* Result: GitHub will automatically create a "Pre-release" named v0.3.0-dev (Rolling). Every subsequent push to this branch updates this specific release.

### Case B: Promoting a Branch to "Stable"

When the code in `version-0.3.0` is ready for production:

1. **Remove the "Unstable" flag:**

Open `pyproject.toml`.

Locate the line: `version = "0.3.0-dev"`

Change it to: `version = "0.3.0"`

1. **Push to GitHub:**

```sh
git add pyproject.toml
git commit -m "release: v0.3.0 stable"
git push origin version-0.3.0
```

Result: The GitHub Action will detect the version change, uncheck the "Pre-release" box, and mark v0.3.0 as the Latest Release.

### Case C: Fixing a Bug in an Old Version (e.g., v0.1.0)

If a bug is found in the "Stable" $0.1.0$ branch:

1. **Checkout the old branch:**

```sh
git checkout version-0.1.0
```

1. **Fix and Push:**

Make your code changes.

```sh
git commit -m "fix: resolve security vulnerability in v0.1.0"
git push origin version-0.1.0
```

Result: The automation will run, see that the version is still "0.1.0" (Stable), and update the existing v0.1.0 release assets/code on the GitHub Releases page.

## Maintenance Summary for Admins

| Event           | Logic                           | Result                                       |
|-----------------|---------------------------------|----------------------------------------------|
| Push to `*-dev` | `STATUS=unstable`               | Updates Rolling Release (Pre-release)        |
| Push to `X.Y.Z` | `STATUS=stable`                 | Updates/Creates Full Release (Latest)        |
| Sunday Midnight | Checks all `version-*` branches | Synchronizes any "missed" pushes to Releases |

## Prohibitions and warnings

 - **Do not rename branches** once they have been pushed; this breaks the link to existing GitHub Releases.
 - **Do not edit** `.github/workflows/release-manager.yaml` on individual version branches. All workflow changes must be made on `master` and then merged/checked-out into the version branches.
 - **Version String Match:** Ensure the tag in pyproject.toml matches the branch name (e.g., version `0.2.0` should be on branch `version-0.2.0`).
