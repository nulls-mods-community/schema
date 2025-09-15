# Null's Brawl Mod JSON Schema

We use draft-07 as the language for describing JSON Schema, since the JSON Schema Validator in VS Code does not support versions above this.

This schema also describes some snippets that are specific to VS Code and are not assumed by the JSON Schema format. You can learn more about VS Code-specific features here: https://code.visualstudio.com/docs/languages/json ([Archive](https://web.archive.org/web/20250914171533/https://code.visualstudio.com/docs/languages/json))

For further info on JSON Schema specification see: https://json-schema.org/specification

## Name suggestions from tables

The current schema allows JSON Schema tools to suggest `properties` names (table columns), and also assumes suggestions for `propertyNames` (table rows) via `examples`.

However, in the current version of VS Code (1.104.0), suggestions for `propertyNames` via `examples` are not implemented. A Pull Request with a fix has already been submitted, so we just have to wait.

### VS Code Patch

If you want to use this schema fully, you can add this feature to your VS Code with a small patch.

In the file `%LOCALAPPDATA%\Programs\Microsoft VS Code\resources\app\extensions\json-language-features\server\dist\node\875.jsonServerMain.js`, after the 207547th character, insert this piece of code:
```js
if(n.examples)for(let t=0;t<n.examples.length;t++){e(n.examples[t],undefined,undefined,undefined)};
```

## TODO

### Array support

Currently, the patches schema does not have arrays as values. It is planned to add them later, but only where it makes sense. As an MVP, find arrays using a script (for rows with an empty first column, see which columns are NOT empty).

### Embedded-patches support

Currently, the schema does not support using patches alongside metadata. This was not added due to draft-07 limitations, since you cannot simultaneously combine different schemas (`allOf`) and prohibit `additionalProperties`.

Possible solutions:

1) Allow embedding patches in `@patches`; in this case, you can abandon the @ prefix, since all root tags will become meta-tags.
2) Automatically generate a file with a combined declaration of `properties` from `generated/patches.schema.json` and `schema.json`, `feature.schema.json`. In this case, the user can choose the desired version themselves. This also allows keeping the prohibition on `additionalProperties`.
3) Use `allOf`, allowing the use of extra properties.

## Ideas

### Should `@enabled` be required if there is a non-empty `@conflicts`?

In fact, such a requirement does not exist at the time of signing the modification. The only requirement is to resolve all conflicts before signing. However, if you force the use of `@enabled`, it will improve development convenience, as users will resolve conflicts immediately.

## License

This project is distributed under the MIT License.  
The full text of the license can be found in the [LICENSE](./LICENSE) file.
