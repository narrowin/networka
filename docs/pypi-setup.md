# PyPI publishing setup

Stable releases use a PyPI API token scoped to the `networka` project, stored as `PYPI_API_TOKEN` in the GitHub `pypi` environment. Prereleases use Trusted Publishing to TestPyPI.

## Set up stable publishing

1. Sign in to [PyPI token creation](https://pypi.org/manage/account/token/).
2. Set the token name to `networka-github-actions` and its scope to **Project: networka**. Create it and copy the token.
3. Run this command in your terminal and paste the token at its hidden prompt:

   ```sh
   gh secret set PYPI_API_TOKEN --repo narrowin/networka --env pypi
   ```

4. Confirm that the secret name appears. This command displays names, never values:

   ```sh
   gh secret list --repo narrowin/networka --env pypi
   ```

The token belongs only in the GitHub environment secret. It is not needed in this checkout or in chat. Revoke it in PyPI when replacing it.

## Release

Follow the pre-release checks in [Project development](development.md#building-and-releasing). The release helper updates metadata and pushes the branch and tag. GitHub Actions builds the distribution files, installs each independently on Ubuntu and macOS, then publishes them. The GitHub release is created only after publication succeeds.

To build and publish an existing release tag using the current workflow:

```sh
gh workflow run release.yml --repo narrowin/networka --ref main -f tag=v0.5.2
gh run list --repo narrowin/networka --workflow release.yml --limit 3
gh run watch RUN_ID --repo narrowin/networka --exit-status
```

The tag must exist remotely and contain matching package metadata. Run a new release only once: PyPI does not permit replacing published files. Retrying a release whose files were already uploaded requires checking which files are present first.

## Why stable publishing uses an API token

The latest checked release run, [0.4.1](https://github.com/narrowin/networka/actions/runs/45694239016), passed its build and both installation jobs. PyPI then returned HTTP 403: the Trusted Publishing token was not allowed to upload to `networka`. Earlier investigation confirmed token issuance but could not establish the server-side permission condition. Manual uploads using a project-scoped API token succeeded; the stable workflow uses that authentication method as a workaround.

The workflow stops with an explicit error if `PYPI_API_TOKEN` is missing. Token-based uploads do not generate Trusted Publishing attestations. Restoring Trusted Publishing remains separate work; the workaround does not claim to fix PyPI's authorization problem. See the [qualification record](development/networka-release-qualification.md#published-020-and-hosted-checks) and [the action's authentication documentation](https://github.com/pypa/gh-action-pypi-publish#specifying-a-different-username).

## TestPyPI

For prereleases, configure a GitHub Trusted Publisher on TestPyPI for owner `narrowin`, repository `networka`, workflow `release.yml`, environment `testpypi`. The GitHub environment must have that exact name. This path remains independent of the stable PyPI token.
