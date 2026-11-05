# Security policy

Report a vulnerability or an unauthorized change to the site privately by email to
**linekginfo@gmail.com**. Do not open a public issue for security problems. The same
contact is published at <https://line.kg/.well-known/security.txt>.

## How the site is protected

- Production is a static site served by GitHub Pages from the `gh-pages` branch.
  There is no server, database, form handler or login to attack.
- Every published page carries a Content-Security-Policy meta tag that allows only
  files from `line.kg` itself, no inline scripts, no plugins and no form submissions.
- Changes reach the site only through commits to `main` and the publishing command
  in [GITHUB-PAGES.md](GITHUB-PAGES.md), run by a repository owner.
- `.github/CODEOWNERS` assigns every file to the repository owner.

Repository and account settings (two-factor authentication, branch rules,
collaborators, Pages domain verification, DNS) are listed in
[GITHUB-PAGES.md](GITHUB-PAGES.md#securing-the-repository-and-domain).
