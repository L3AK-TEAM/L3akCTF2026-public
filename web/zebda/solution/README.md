# Zebda

### Author: Minyawy

## Summary

The challenge runs your input through two programs that read it differently. A Node/Express service sits in front and validates the request, and a Python worker behind it actually runs the job. The idea is to make those two disagree, so the front service sees something harmless while the worker does something else.

You have to pull this off in two separate places and combine them. Neither one gets you the flag on its own.

## How the app works

Traffic goes through nginx to the Node middleware. You create a project with a slug, then send that project a YAML build manifest. The middleware parses the manifest with js-yaml, checks that the action is `translate` and the source is an HTTPS URL, and forwards the original slug and the raw manifest text to the worker.

The worker parses the same YAML again with PyYAML. It also normalizes the slug and picks a policy from it. Normal projects may only `translate`. A project whose normalized slug is `system` also gets `import`, which reads `/flag.txt`.

So the flag needs two things at the same time: a project the worker treats as `system`, and a manifest that the middleware reads as a `translate` job while the worker reads it as an `import`.

## Getting the system policy

The middleware refuses reserved names:

```js
const reservedNames = new Set(["system", "admin"]);
reservedNames.has(slug.toLowerCase());
```

It only lowercases the slug. The worker normalizes it with Unicode NFKC instead:

```python
unicodedata.normalize("NFKC", slug).casefold()
```

The fullwidth letters in `ｓｙｓｔｅｍ` are different code points from the ASCII ones, so `toLowerCase()` leaves them unchanged and the name passes the reserved check. NFKC then collapses them back to plain `system`, so the worker gives the project the system policy. Registering a project with the slug `ｓｙｓｔｅｍ` gets you past the name check while still counting as `system` on the back end.

You do not have to convert the whole word. A single fullwidth letter is enough. The middleware check only needs the string to be anything other than exactly `system`, and NFKC still folds the rest back to `system`. So `systeｍ` (only the last letter fullwidth) or `ｓystem` (only the first) work just as well as the fully converted version.

That is not enough by itself. A manifest that asks for `import` directly still gets rejected by the middleware, because the action is not `translate`.

## The YAML parser difference

js-yaml and PyYAML disagree about what to do when a mapping has two merge keys. Take this manifest:

```yaml
job:
  <<: {action: translate, source: "https://example.com/dict.json"}
  <<: {action: import, source: "file:///flag.txt"}
```

js-yaml 4.1.0 applies the first `<<` and ignores the second, because its merge only fills in keys that are not already set. It ends up with `action: translate` and an HTTPS source, which passes validation.

PyYAML flattens both merge keys and lets the last one win, so it ends up with `action: import` and `source: file:///flag.txt`.

The middleware forwards the raw text without changing it, so the worker parses the exact same bytes and reaches the opposite result.

A few approaches that do not work, for context:

- Two plain `action:` keys. js-yaml 4.x throws a duplicate key error.
- One `<<` plus an explicit key. Both libraries let the explicit key win, so there is no difference between them.
- Bumping js-yaml to 5.x. That version dropped merge key support and treats `<<` as an ordinary string key, which kills the trick. This is why the version is pinned to 4.1.0.

## Reading the flag

1. Send a fullwidth unicode slug to be interpreted as `system` by the worker and bypass the frontend block: `ｓｙｓｔｅｍ`
2. Send duplicate `<<` merge keys. When PyYAML merges them it keeps the second one, so we can use `action: import` to get the flag with the `file://` scheme as the source

```yaml
job:
  <<: {action: translate, source: "https://example.com/dict.json"}
  <<: {action: import, source: "file:///flag.txt"}
```

## References

- [Black Hat USA 2025 | Lost in Translation: Exploiting Unicode Normalization](https://www.youtube.com/watch?v=ETB2w-f3pM4)
- [OffensiveCon25 - Joernchen - Parser Differentials: When Interpretation Becomes a Vulnerability](https://www.youtube.com/watch?v=Dq_KVLXzxH8)
- [Hacky](https://hacky.uk/allLabs)
- [DarkForge Labs - YAML Merge Tags and Parser Differentials](https://blog.darkforge.io/yaml/merge/parser/differential/research/2026/02/11/YAML-Merge-Tags-and-Parser-Differentials.html)

