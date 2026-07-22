# Nuevo repositorio GitHub (pendiente de permisos)

El Cloud Agent intentó crear un repositorio GitHub privado dedicado:

```text
cygnusbarrett/consejos-guerra-grafo-multimodal
```

pero el token de la integración no tiene permiso `createRepository`
(`GraphQL: Resource not accessible by integration`).

Mientras tanto, este mismo repo (`dataframe-crossing`) aloja el código en la
rama de trabajo. Para crear el repo canónico desde tu cuenta:

```bash
gh repo create cygnusbarrett/consejos-guerra-grafo-multimodal \
  --private \
  --source=. \
  --remote=mmg \
  --description "Grafo multimodal — Consejos de Guerra (Museo de la Memoria)"

git push -u mmg cursor/grafo-multimodal-consejos-guerra-e698
```

O renombrar este repositorio en GitHub Settings si ya no se usará para el
cruce de dataframes (los notebooks previos quedaron en
`archive/dataframe-crossing/`).
