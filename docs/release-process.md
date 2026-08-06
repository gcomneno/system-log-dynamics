# Release process

This process applies to the first public 0.1.0 milestone and subsequent
corrective releases. It describes maintainer actions; none are performed by
ordinary validation.

## Before approval

1. Ensure the intended release commit or pull request contains only reviewed
   release changes and has passed complete validation.
2. From the repository root, run formatting, lint, tests, and compilation:

   ```console
   python -m ruff format --check .
   python -m ruff check .
   python -m pytest -q
   python -m compileall -q src tests
   ```

3. Build outside the repository and inspect the artifacts:

   ```console
   RELEASE_VALIDATE_DIR="$(mktemp -d)"
   python -m build --outdir "$RELEASE_VALIDATE_DIR/dist"
   tar -tzf "$RELEASE_VALIDATE_DIR/dist/system_log_dynamics-0.1.0.tar.gz"
   unzip -l "$RELEASE_VALIDATE_DIR/dist/system_log_dynamics-0.1.0-py3-none-any.whl"
   rm -rf "$RELEASE_VALIDATE_DIR"
   ```

   The artifact review must confirm the changelog, release documentation,
   decisions, Experiment 001 documentation, and synthetic fixtures are
   present, while private journals and generated trees are absent.

4. Create a fresh virtual environment outside the repository, install the
   wheel with its immutable dependencies, check installed metadata, and run
   the installed `analyze` and `compare` commands against Experiment 001
   fixtures. Use a synthetic `journalctl` executable for any `collect` check;
   never access the host journal during validation.

## Approval and publication

After the final release commit or pull request is approved, squash-merge it
according to the repository policy. Create an annotated tag named `v0.1.0`
on the resulting merge commit, not on an unmerged branch commit. Publish
GitHub Release notes that summarize the bounded contract, dependency pin, and
limitations, and link the changelog and release note.

Artifact publication to a package index is optional. Do it only after the
GitHub Release and only through an explicitly approved publishing workflow;
a tag never authorizes automatic artifact publication.

## After publication

Verify that the annotated tag resolves to the intended merge commit, the
GitHub Release notes are correct, any intentionally published artifact has
the expected version and contents, and a clean isolated installation reports
`0.1.0` in both package and distribution metadata.

If a released artifact or tag is wrong, do not rewrite public history. Stop
publication where possible, document the defect, and issue a new corrective
version with its own validation, annotated tag, and release notes.
