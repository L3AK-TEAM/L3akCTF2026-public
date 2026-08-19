# Omega

Omega is a job executor: it accepts jobs and runs them inside its virtual
machine. The flag is at `/challenge/flag.txt` on the server.

## What's here

| File              | Description                          |
| ----------------- | ------------------------------------ |
| `executor`        | The executor binary the server runs. |
| `echo.remote.prx` | An example job; runs on the remote.  |
| `echo.local.prx`  | The same job, for local runs.        |

## Running locally

```
SECRET=00112233445566778899aabbccddeeff ./executor echo.local.prx
```
