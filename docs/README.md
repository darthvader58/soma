# SOMA Mintlify documentation

This directory is the Mintlify source root. It documents the repository's actual `soma-lunar` 0.1.0 library, local service, export contract, and scientific limits.

Use Node.js 20.17 or newer. From this directory:

```bash
npx --yes mint dev --no-open
npx --yes mint validate
npx --yes mint broken-links --check-anchors
```

The current CLI package is `mint`, not the legacy `mintlify` package. Configuration is `docs.json` and navigation entries resolve to MDX pages without extensions.

## Publish with Mintlify

1. Sign in to the official dashboard at https://app.mintlify.com/ and create or select the documentation project.
2. Connect the GitHub repository `darthvader58/soma` with the intended repository permissions.
3. Open https://app.mintlify.com/settings/project/git-settings, select the desired production branch, enable **docs.json is in a subdirectory**, and enter `docs` so Mintlify reads `docs/docs.json`.
4. Build and inspect the exact hosted documentation URL assigned by Mintlify. Confirm every navigation group, Python code example, internal link, and narrow/mobile layout.
5. Configure the application's Documentation link with that verified URL, or map `/docs` to it after the site exists. A local `/docs` route alone does not publish a Mintlify site.
6. If desired, configure a custom documentation domain in Mintlify and add its prescribed DNS records, then verify HTTPS before switching links.

The source does not create a Mintlify account, provision hosting, or claim the documentation is already published. Dashboard access and repository authorization are required for hosted deployment.

Official references: https://www.mintlify.com/docs/quickstart and https://www.mintlify.com/docs/cli/commands.
