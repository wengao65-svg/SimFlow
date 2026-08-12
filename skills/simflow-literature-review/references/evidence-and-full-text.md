# Evidence And Full Text

## Evidence Boundaries

- `metadata_only`: bibliographic metadata or abstract is available.
- `full_text_available`: a lawful URL or user-provided file is available, but
  the relevant content has not been inspected.
- `full_text_inspected`: identified pages or sections were actually read.
- `claim_verified`: a specific claim was checked against explicit full-text
  locators. This status applies only to that claim.

Never promote evidence based on file existence, successful download, parser
success, abstract availability, or provider count alone.

## Full-Text Order

1. User-provided local full text.
2. arXiv or another author-hosted preprint.
3. Legal open-access locations from scholarly indexes or repositories.
4. Publisher APIs or the user's own institutional entitlement through an
   optional host-managed adapter.

Institutional login, SSO, 2FA, CAPTCHA, cookies, and credentials remain outside
SimFlow. The user completes authentication in the external tool or visible
browser. SimFlow may consume only a resulting entitled candidate with an
explicit access basis.

Do not use or recommend Sci-Hub, LibGen, access-control bypass, credential
capture, stealth browsing, or anti-bot circumvention as SimFlow retrieval
routes.
