# DiveTopo

Homepage générale de [divetopo.com](https://divetopo.com). Elle présente les
cartographies de sites de plongée disponibles par région et renvoie actuellement
vers les cartes de [La Réunion](https://reunion.divetopo.com).

La liste des régions est centralisée dans `content/regions.ts`. Ajouter une
région consiste à déposer son image dans `public/`, puis à ajouter une entrée
dans ce tableau ; la grille et les libellés sont rendus automatiquement.

La page existe en français et en anglais. Au premier accès, la langue suit celle
du navigateur, puis le choix FR/EN est conservé dans un cookie. Le thème propose
Clair, Sombre et Auto ; Auto est le réglage initial et suit le mode du système.
Sur les domaines DiveTopo, ces préférences sont partagées avec les atlas
régionaux, notamment `reunion.divetopo.com`.

## Développement

```bash
npm install
npm run dev
npm test
```

Le projet utilise vinext et produit un build compatible avec Sites. Son
identifiant de projet Sites est conservé dans `.openai/hosting.json`.
