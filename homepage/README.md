# DiveTopo

Main homepage for [divetopo.com](https://divetopo.com). It presents the
available dive-site maps by region and currently links to
[Topo Réunion](https://reunion.divetopo.com).

The list of regions is centralized in `content/regions.ts`. To add a region,
place its image in `public/`, then add an entry to this array; the grid and
labels are rendered automatically.

The page is available in French and English. On the first visit, the language
follows the browser setting, after which the FR/EN choice is stored in a
cookie. The theme offers Light, Dark, and Auto; Auto is the initial setting and
follows the system mode. Across DiveTopo domains, these preferences are shared
with the regional mapping pages, including Topo Réunion at
`reunion.divetopo.com`.

## Development

```bash
npm install
npm run dev
npm test
```

The project uses vinext and produces a Sites-compatible build. Its Sites
project identifier is stored in `.openai/hosting.json`.
