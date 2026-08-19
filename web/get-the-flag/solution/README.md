# Get The Flag  Solution
### Author: Minyawy

## Walkthrough

The flag is at `/flag` but it's only accessible to the admin user. We can't just visit it, the server checks our role from the database and returns "Access Denied" if we're not admin. The admin has a random 64-character password so brute force isn't an option. But there's a "Report URL" feature that makes the admin bot visit a page we control, and a `/account/change-password` endpoint that lets any logged-in user change their own password. If we can get the admin to hit that endpoint with a password we choose, we win.

The app has CSRF protection in place. Looking at `app.js`, the middleware that handles this is:

```js
function csrfOnPostOnly(req, res, next) {
  if (req.method !== "POST") {
    return next();
  }

  if (!req.body.csrf || req.body.csrf !== req.session.csrf) {
    return res.status(403).send("Invalid CSRF token");
  }

  next();
}
```

Every POST request needs a valid CSRF token, and without it we get a 403 back. So a plain cross-site form submission won't work. But this middleware only enforces the check when `req.method === "POST"`, anything else gets a free pass.

Now, earlier in the middleware stack we can see the app also registers `method-override`:

```js
app.use(
  methodOverride((req) => {
    if (typeof req.query._method === "string") {
      return req.query._method.toUpperCase();
    }
  })
);
```

This runs *before* the CSRF check. It reads `?_method=` from the query string and overwrites `req.method` with whatever we pass. The key bug is that the CSRF middleware checks `req.method` (the overridden value) instead of `req.originalMethod` (the actual transport method). So if we send a real POST but append `?_method=GET` to the URL, the middleware rewrites the method to GET before CSRF validation runs. The server skips the token check because it thinks it's a GET ,  but the POST body with our new password is still parsed and available.

Note that uploaded pages are served with a CSP header (`connect-src 'none'; frame-src 'none'; object-src 'none'`), so you can't just use `fetch()` or XHR to grab the CSRF token from `/account/change-password` and POST it back , the browser blocks all programmatic requests. The method-override trick is what makes this solvable: a plain HTML form submission isn't restricted by `connect-src`, so the CSRF bypass via `?_method=GET` is the intended path.

We register an account, log in, and create a page through the "Create Page" feature with this self-submitting form:

```html
<form id=f method=POST action="/account/change-password?_method=GET">
  <input name=password value=HackedPass1!>
  <input name=confirm value=HackedPass1!>
</form>
<script>f.submit()</script>
```

We take the `/pages/xxx.html` path we get back and submit it to the admin bot via the "Report URL" page. The bot logs in as admin, visits our page, and the form auto-submits ,  changing the admin's password to `HackedPass1!` without needing a CSRF token. Now we just log in as `admin` with that password and visit `/flag`.

```bash
python3 solve.py http://localhost:13337
```

## References

- [Express method-override middleware](https://github.com/expressjs/method-override)
