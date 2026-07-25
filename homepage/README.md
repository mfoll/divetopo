# DiveTopo

Main homepage for [divetopo.com](https://divetopo.com). It presents the
available dive-site maps by region and currently links to
[Topo Réunion](https://reunion.divetopo.com).

The list of regions is centralized in `content/regions.ts`. To add a region,
place its image in `public/`, then add an entry to this array; the grid and
labels are rendered automatically.

The canonical language routes are `/fr` and `/en`. The root URL redirects to
the saved language, then to the preferred supported browser language. The
FR/EN control navigates between the stable routes and stores the choice in a
cookie. The theme offers Light, Dark, and Auto; Auto is the initial setting and
follows the system mode. Across DiveTopo domains, these preferences are shared
with the regional mapping pages, including Topo Réunion at
`reunion.divetopo.com`.

Search engines receive self-referencing canonical URLs, reciprocal language
alternates, an `x-default` root URL, structured data, `robots.txt`, and
`sitemap.xml`.

## Development

```bash
npm install
npm run dev
npm test
```

The project uses vinext and produces a Sites-compatible build. Its Sites
project identifier is stored in `.openai/hosting.json`.
