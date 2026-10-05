# Marie Parie Web

Simple website for **Marie Parie Boutique**.

The site is intentionally lightweight and can be deployed as a static front end to an Azure App Service.

## Files

- `index.html` — main landing page

## Deployment

The repository is connected to Azure App Service through **Deployment Center / GitHub Actions**.

- `main` deploys to the live Marie Parie website.
- `staging` deploys to the staging website used for review and approval before release.

For a simple Windows App Service deployment, the published site content should end up under:

`site/wwwroot`

## Development

No build step is required for the site. Open `index.html` directly in a browser for local testing.

### Branch policy

Use the following branch flow for all website development:

```text
main
  ↓
staging
  ↓
work / feature branches
```

The branch roles are:

- **`main`** — production only. This is the version currently intended for the live public website.
- **`staging`** — the integration and review branch. Changes merged here are deployed to the staging website so Arla and Heidi can review them before they go live.
- **Work branches** — create all normal development branches from `staging`, not from `main`. Examples: `feature/homepage-update`, `feature/new-collection`, or `fix/mobile-layout`.

The normal procedure is:

1. Start from the latest `staging` branch.
2. Create a work/feature/fix branch from `staging`.
3. Make and test the change on that work branch.
4. Merge the work branch back into `staging`.
5. Review the deployed staging website.
6. When the changes are approved for production, merge `staging` into `main`.
7. Do not merge ordinary work branches directly into `main`.

In short:

```text
work branch → staging → main
```

When assisting with repository changes, ChatGPT or any other automated development tool should consult and follow this branch policy before creating branches, pull requests, or merges.
