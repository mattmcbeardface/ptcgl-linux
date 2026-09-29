# Security

## Sensitive data

Do not submit:

- Pokémon account credentials
- OAuth callback URLs
- authorization codes
- access or refresh tokens
- Wine prefix contents containing user data
- diagnostic logs containing credentials or authentication URLs

The launcher must never intentionally persist the complete
`tpcitcgapp://` authentication callback.

## Vulnerability reports

Until a dedicated reporting process exists, do not publish secrets or account
data in a public GitHub issue.
