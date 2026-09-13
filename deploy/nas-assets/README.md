# NAS robot assets

Serves versioned URDF/STL assets at `https://robot-assets.timo0604.xyz:5000/models/`.

- `robot-assets-acme` reads the existing ddns-go AliDNS configuration through a read-only mount and renews the certificate with DNS-01.
- `robot-assets` serves files with CORS, cache and byte-range support.
- `gateway-nginx.conf` keeps existing plaintext HTTP sites on port 5000 and forwards TLS traffic to `robot-assets` using Nginx stream preread.

The NAS deployment directory is `/volume2/SSD/project/robot-assets`. The existing gateway config must be backed up before installing `gateway-nginx.conf`.
