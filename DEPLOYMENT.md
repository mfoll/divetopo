# DiveTopo deployment model

GitHub and the hosted website have different roles:

- `main` on GitHub is the canonical source and history for the complete
  project;
- `apps/web/` is the only deployable application;
- [divetopo.com](https://divetopo.com) serves the general homepage, regional
  pages, site pages, maps and interactive terrain.

There is no automatic GitHub-to-Sites deployment hook. A GitHub push does not
update the hosted site by itself.

## Routes

The unified application publishes:

```text
https://divetopo.com/fr
https://divetopo.com/en
https://divetopo.com/reunion
https://divetopo.com/reunion/fr
https://divetopo.com/reunion/en
https://divetopo.com/reunion/{language}/sites/{site-slug}
```

The neutral roots select the saved or preferred language. Canonical URLs,
reciprocal `hreflang` alternatives, `x-default`, structured metadata,
`robots.txt` and the single `sitemap.xml` all use `divetopo.com`.

`reunion.divetopo.com` is not part of the target architecture and is not
redirected. Its former Sites project may remain dormant as a rollback snapshot,
without a custom domain.

## Synchronization invariant

Sites stores the Web application in its own internal source repository. Its
commit SHA therefore differs from the root GitHub commit. Synchronization is
proved by tree equality:

```text
tree(GitHub HEAD:apps/web) == tree(Sites source commit)
```

The saved Sites version must reference that internal source commit, and the
production deployment must reference that saved version. Similar messages or
timestamps are not evidence.

A change outside `apps/web/` does not require deployment when the application
tree is unchanged. A changed regional output does require rebuilding its
publication derivatives before the application tree can be considered current.

## Release sequence

1. Inspect the current branch and the complete task-scoped diff.
2. Run the relevant regional configuration checks and the Python suite.
3. When cartographic artifacts were moved rather than regenerated, verify their
   SHA-256 hashes against the pre-migration inventory.
4. Run `npm run lint` and `npm test` in `apps/web/`.
5. Inspect the general and regional routes, language/theme controls, map
   switching, downloads and interactive terrain on desktop and mobile.
6. Commit and push the complete reviewed state to GitHub.
7. Resolve the exact subtree with `git rev-parse HEAD:apps/web`.
8. Push that exact tree to the existing DiveTopo Sites source repository.
9. Build and package the same source tree.
10. Save a Sites version referencing its source commit and deploy that saved
    version.
11. Confirm the deployment, custom domain, public access, sitemap, assets and
    tree equality.

Never deploy an uncommitted directory or a tree assembled from mixed repository
states.

## Operational boundaries

- `apps/web/.openai/hosting.json` identifies the existing DiveTopo Sites
  project. Treat its project identifier as opaque.
- Deployment credentials are short-lived and must never be committed.
- The cartographic pipeline owns canonical maps, sheets and interactive
  terrain. The Web application only publishes verified derivatives.
- A Codex task, local worktree or chat history is never a source of truth.
  Durable state belongs in Git, this documentation and the linked project
  notes.
