## Omega

### Author: Atzr

Description: "One must imagine Sisyphus happy." - Camus

Flag: `L3AK{M45k3d_1n$truct!on5_P3rmu+ed_5u8s+1tut3d_954247ee}`

## Deploying

Using Docker Compose (recommended):

```sh
docker compose -f build/docker-compose.yml up --build -d
```

Or with plain Docker:

```sh
docker build -f build/Dockerfile -t omega .
docker run --rm --privileged -p 5000:5000 omega
```
