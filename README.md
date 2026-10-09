# Marie Parie Web

Simple website for **Marie Parie Boutique**.

The website is a lightweight static front end; no build step is required.

## Files

- `index.html` — main landing page

## Deployment

- `main` deploys to the live Marie Parie website using the existing production deployment.
- `staging` is published through **Cloudflare**, which Arla uses to review changes before production.
- **Do not deploy the static staging website to Azure App Service.** The Azure staging App Service plan hit quota/tariff limits and blocked GitHub deployments. Its GitHub Actions workflow was removed.
- The **Azure contact API is separate**: changes under `api/` can still trigger the dedicated contact API workflow. Do not disable it when making changes to the static website deployment.

Cloudflare is the authoritative preview site for the `staging` branch. Be sure Cloudflare Turnstile and the Azure contact API allow the staging hostname before testing form submissions.

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
- **`staging`** — integration and review branch, automatically published to Cloudflare for Arla and Heidi to review before release.
- **Work branches** — create all normal development branches from `staging`, not from `main`. Examples: `feature/homepage-update`, `feature/new-collection`, or `fix/mobile-layout`.

The normal procedure is:

1. Start from the latest `staging` branch.
2. Create a work/feature/fix branch from `staging`.
3. Make and test the change on that work branch.
4. Merge the work branch back into `staging`.
5. Review the Cloudflare staging website.
6. When approved for production, merge `staging` into `main`.
7. Do not merge ordinary work branches directly into `main`.

In short:

```text
work branch → staging (Cloudflare preview) → main (production)
```

When assisting with repository changes, ChatGPT or any other automated development tool should consult and follow this branch policy before creating branches, pull requests, or merges.
