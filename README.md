# Null's Brawl Mod JSON Schema

Мы используем draft-07 в качестве языка для описания JSON Schema, так как JSON Schema Validator у VS Code не поддерживает версии выше.

https://json-schema.org/specification

Также эта схема описывает некоторые snippets, которые специфичны для VS Code и не предполагаются форматом JSON Schema. Подробнее о VS Code-specific функуциях можно узнать здесь: https://code.visualstudio.com/docs/languages/json ([Archive](https://web.archive.org/web/20250914171533/https://code.visualstudio.com/docs/languages/json))

## Идеи

### Требовать ли @enabled, если присутствует не пустой @conflicts?

Фактически такого требования не существует на момент подписи. Обязательным является только разрешить все конфликты фич заранее. Однако если заставить использовать @enabled, то думаю, что это хорошо скажется на разработке, так как люди будут думать об этом сразу, а не после неудачной подписи. 