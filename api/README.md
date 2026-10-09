# Marie Parie contact API

Python Azure Functions v2, independently deployed from the static website. POST /api/contact accepts JSON with kind 'contact' or 'mailing list', firstName, lastName, email, turnstileToken, and message (contact) or phone + consent=true (mailing list).

Configure in the **Function App settings**, not source control:
- ACS_CONNECTION_STRING: connection string from the existing Azure Communication Services resource
- ACS_SENDER_ADDRESS: verified authorized sending mailbox (for example DoNotReply@<verified-domain>)
- TURNSTILE_SECRET_KEY: private Cloudflare Turnstile secret
- TURNSTILE_ALLOWED_HOSTNAMES: comma-separated exact website hostnames for production and staging
- RATE_LIMIT_SALT: long random application-specific value
- AzureWebJobsStorage: normal Function App storage connection string for shared rate-limit counters
- GLOBAL_DAILY_LIMIT: optional, defaults to 100

Create Azure Table `MarieParieFormLimits` in Function storage (or ensure it exists during provisioning). No secrets or customer-submitted content should be put in logs. Protect function access through Turnstile verification, fixed destination, form validation, and shared optimistic-concurrency counters. Configure Azure monitoring/cost alerts and review ingress/WAF protection. Table counters are time-bucketed and can be purged after 48 hours. IP data is stored only as salted hashes. If trusted client IP headers are unavailable, per-IP rates collapse to a shared 'unknown' bucket; configure a trusted edge before production for reliable client attribution.

The frontend needs the Turnstile public **site key** and the endpoint URL. A client site key is not a secret. Set allowed origins on Function App CORS to the staging and production websites. CORS is browser isolation only, not a security boundary. The endpoint is intentionally anonymous because the public website cannot safely store a Function key.

Never merge into staging until a deployed Function endpoint and Turnstile site key are configured and tested. Deleting the WordPress deployment must not delete the two ACS resources.

## Public Turnstile widget

Cloudflare Turnstile **site key** (public, safe for browser): `0x4AAAAAAFR4-OgtnoP1yPRi`.
Use this for both form widgets on the approved hostnames. Keep the separately generated **secret key** only in the Function App setting `TURNSTILE_SECRET_KEY`.

Do **not** change live form submission behavior until `POST /api/contact` is deployed, its public URL is known, CORS/allowed hostnames are configured, and end-to-end test email delivery succeeds. Existing staging forms currently still use mailto.

## GitHub Actions deployment

The independent workflow is at `.github/workflows/contact-api.yml`; it tests with Python 3.14 and deploys only the `api/` directory to `marie-parie-contact-api`. It runs on API changes merged into `staging` or a manual dispatch. Do not merge until the infrastructure and workflow identity are ready.

Configure OIDC using an Entra application/service principal with a federated GitHub subject `repo:junwin/marie-parie-web:ref:refs/heads/staging`, audience `api://AzureADTokenExchange`, and sufficient scoped deploy permissions to the Function App. Create these GitHub **Actions secrets**:

- `MARIE_PARIE_FUNCTION_CLIENT_ID` — Entra application client ID (not ACS credential)
- `MARIE_PARIE_FUNCTION_TENANT_ID`
- `MARIE_PARIE_FUNCTION_SUBSCRIPTION_ID`

These are Azure login identifiers, distinct from Function App *environment variables* above. Do not put the ACS connection string or Turnstile secret in GitHub. This workflow does not alter the existing static-site deployment workflows.

For a pre-merge test from the feature branch, add a separate federated identity subject for `refs/heads/feature/secure-contact-api` and run the workflow there (provided it is available for manual dispatch). Do not copy the website's existing Deployment Center credentials blindly; its federated trust may be scoped to the website's workflow and branch.
