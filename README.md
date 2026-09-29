# Knight Sat Sim

A **Platform** for practicing satellite cybersecurity and learning ground-station operation, including the station at UCF’s Physical Sciences Building (PSB). **Players** practice with simulated systems and learn the equipment and workflow used at PSB.

This repository is **Knight Sat Sim (KSS)**, the UCF CS Senior Design implementation of that Platform. The product has three tracks: **Basic operations**, **Offensive**, and **Defensive**. The first version to build (MVP) focuses on **three Basic operations Challenges**, **Hello, Satellite!**, **Ready for the Pass**, and **Catch and Log**. Completion is based on performing the tasks, without submitting Flags. The specs define the agreed learning flow and implementation defaults. Offensive and Defensive Challenges come later. Practice remains browser-based, without live station-hardware integration. See the [ground-station training plan](docs/specs/ground-station-training.md).

Start with the [project plan](docs/specs/project-plan.md) for scope, responsibilities, progression, and completion checks. Its [build specifications](docs/specs/project-plan.md#build-specifications) table links to the implementation and learning documents. Each spec owns its decisions; research provides supporting sources, not additional MVP requirements.

## Repository layout

| Path | Contents |
| --- | --- |
| `server/sim/` | Sim Service, packet handling, Ground Sim, and Software Link |
| `server/api/` | FastAPI Web Backend |
| `ui/` | React and TypeScript frontend |
| `docs/specs/` | Current scope, architecture, behavior, and acceptance checks |
| `docs/research/` | Supporting sources and technical findings |

The repository currently contains a scaffold. Running it starts the frontend and backend health endpoint; it does not provide the planned Challenges, terminal, database behavior, or station lessons yet.

## Run locally

You need Docker. From the repository root:

```bash
docker compose up --build
```

- Browser UI: http://localhost:5173
- Web Backend health check: http://localhost:8000/health

Compose starts the React development server and **one** Python process that will contain FastAPI and the Sim Service. The `sqlite-data` volume is reserved for the planned SQLite progress database. Do not run extra server workers: the MVP Attempt lives in memory in that single process.

Without Docker:

- Server: Python 3.12+, from `server/`: `uv sync` then `uv run uvicorn api.main:app --reload --host 0.0.0.0 --port 8000` (still one worker).
- UI: Node 22+, from `ui/`: `npm install` then `npm run dev`.

## Home server administration

On Diab's Mac, connect Tailscale and run `ssh knightsat` to administer Ubuntu, at home or away. The shortcut uses the VM's private Tailscale name `knight-sat-sim.tailfa2021.ts.net` (currently `100.108.206.107`). `ssh knightsat-lan` is the home-network fallback. Agents running on this Mac can use these same SSH commands without the browser console. Other computers need their own authorized SSH key and access to the same tailnet; these shortcuts are local to this Mac.

SSH uses `~/.ssh/id_ed25519_knightsat` for the existing `diab` account, with the VM host key verified through Proxmox and pinned under `knightsat-vm`. Password and root SSH logins are disabled. The private key stays on the Mac, outside this repository. Use `sudo` for administration; its password is unchanged and still required. No router port forwarding or public SSH endpoint is configured. Tailscale provides the private network connection; authentication uses ordinary OpenSSH, not Tailscale SSH.

The VM's Tailscale device key currently expires on **2027-03-27**; reauthenticate it before expiry for uninterrupted remote access. The Mac must remain connected to Tailscale, and the HP and home internet must be running. Key-authenticated login through the Tailscale address and rejection of password/root SSH login were verified on 2026-09-28. Fresh off-site Tailscale SSH connections over IPv4 and IPv6 passed during the 2026-09-28 audit; recheck after network or device changes.

For recovery on Diab's home network, open [Proxmox](https://192.168.1.50:8006/) and select **OGnode → 100 (knight-sat-sim) → Console**. The Ubuntu password is separate from the Proxmox `root@pam` login and belongs in a private password manager, never this repository. Proxmox itself remains accessible only on the home network.

VM 100 uses Ubuntu Server 24.04 LTS, 2 virtual CPUs, 4 GiB RAM and a 40 GiB disk on `local-lvm`, with automatic startup enabled. Its network adapter is `enp6s18`, connected to `vmbr0`, with MAC address `BC:24:11:DB:1E:3D`. The current DHCP address is `192.168.1.52`; check **Summary → IPs** or `ip -4 -brief address` after a restart. Reserve the VM's address in the home router before relying on it for deployment. Keep the Proxmox management address private.

Docker Engine, Buildx and the Compose plugin are installed inside the VM from [Docker's official Ubuntu APT repository](https://docs.docker.com/engine/install/ubuntu/). The Ubuntu `qemu-guest-agent` package lets Proxmox report the guest's address and request a clean shutdown. Use those sources when rebuilding the VM. Run Docker through `sudo`; Docker administration must remain separate from Player execution permissions.

After maintenance or a restart, check the VM over SSH or from its console:

```bash
systemctl --failed
systemctl is-active ssh tailscaled docker qemu-guest-agent
sudo docker run --rm hello-world
sudo docker compose version
df -h /
```

Use **Shutdown** in Proxmox for a clean power-off. VM 100 has a `base-ubuntu-docker` snapshot of the clean installation, taken after successful container and reboot checks. Find it under **VM 100 → Snapshots**. It predates SSH and Tailscale setup: restoring it removes this remote access configuration. It provides a local rollback point before application deployment, but it does not protect against failure of the HP's SSD. Rolling back discards guest changes made after that snapshot.

### Hosted scaffold

The temporary team address is **https://knightsat.radio-ranger.com**. Cloudflare Access allows only `di227923@ucf.edu` using emailed codes, with a six-hour application session. The domain and Zero Trust are on Free plans. Use only free Tunnel and Access features; do not enable paid add-ons or upgrade to bypass a limit without Diab's approval. Budget alerts are not spending caps, and existing domain renewals are separate.

The remotely managed `knight-sat-sim` tunnel (`5c4c16a7-d89d-4d90-83b2-6bac5584e2c3`) routes this hostname to `http://127.0.0.1:8080`. Its per-hostname **Enforce Access JWT validation** setting is enabled for the **Knight Sat Sim** Access application. The connector validates the signed login token before forwarding traffic. Other hostnames fall back to HTTP 404. No private-network routes, public SSH endpoint, or Proxmox route are configured.

`cloudflared` is installed from [Cloudflare's official APT repository](https://pkg.cloudflare.com/). Its enabled systemd service uses a temporary unprivileged identity, a read-only filesystem, and a private systemd credential loaded from `/etc/cloudflared/token` (root-owned, mode 0600). The token never belongs in Git or logs. Route settings live in Cloudflare; service configuration lives in `/etc/systemd/system/cloudflared.service`. To check it, run `systemctl is-active cloudflared` and `sudo journalctl -u cloudflared --since '10 minutes ago'`. Metrics bind only to `127.0.0.1:20241`.

The VM runs the current placeholder UI and health API from `/opt/knightsat`, using `compose.hosting.yml`. This is a separate configuration from development: built static UI behind Nginx, one non-root Python worker, bounded CPU/memory/processes/logs, read-only container images, and a persistent `knightsat_progress` volume. Only the web service publishes a port, on **127.0.0.1:8080**. The backend is on an internal Docker network. Neither service has access to the Docker socket.

To view it privately from the Mac, run `ssh -N -L 127.0.0.1:18080:127.0.0.1:8080 knightsat` and open `http://127.0.0.1:18080`. Stop that SSH command when finished. On the VM:

```bash
cd /opt/knightsat
sudo docker compose -f compose.hosting.yml ps
sudo python3 deploy/check-hosting.py
sudo docker compose -f compose.hosting.yml logs --tail=100
```

`deploy/check-hosting.py` checks HTTP routing and live container protection settings; CI builds the same images and runs it. Dependencies come from the existing npm and uv lockfiles. The initial local image tag is `hosting-20260928`; it identifies this infrastructure trial, not an approved production revision. The manual workflow below uses full main SHAs and digest-pinned GHCR images; the historical trial becomes superseded only after a successful recorded update.

From any computer with Python and internet access, `python3 deploy/check-hosting.py --public` verifies that anonymous requests and malformed credentials redirect to Cloudflare Access for the UI, health, API, internal paths, and a WebSocket upgrade request. This proves edge denial, not individual JWT claim validation or a live application WebSocket. `--origin-only` runs HTTP routing checks on the VM without Docker privileges. On 2026-09-28, the public gate, connector JWT configuration, local HTTP routes, and container protections passed their checks. An approved email-code login reached the hosted placeholder UI. A VM reboot restored SSH, Tailscale, Docker, the tunnel and the health endpoint automatically; the origin and public gate checks passed again afterward. Direct LAN connections to ports 8080 and 8000 failed as intended. Automated Chrome navigation to `/health` returned `ERR_BLOCKED_BY_CLIENT`; Diab subsequently verified signed-in manual Chrome navigation returned `{"status":"ok"}`, matching the local health check.

The placeholder page has no Challenges, ownership/admission controls, progress migrations, terminal, or WebSocket endpoints yet. A temporary SQLite fixture survived container replacement; this validates the volume, not saved Challenge progress. Do not deploy feature updates by directly recreating this stack once Player sessions exist. KSAT-23 supplies immutable revision images through GHCR publishing. KSAT-25 supplies the bounded placeholder **Update website** workflow below; its application admission, busy refusal and migration integration remain required. KSAT-26 must verify the complete hosted user journeys and capacity. Follow the [hosting specification](docs/specs/backend-and-simulation.md#implementation-defaults-hosting) for those requirements.

Backups are intentionally deferred at Diab's request. The persistent volume and local Proxmox snapshot do not provide an off-device backup.

### KSAT-24 acceptance evidence

Audit **2026-09-28**, Chrome **154.0.8037.58**. [KSAT-24](https://seniordesign-g20.atlassian.net/browse/KSAT-24) remains incomplete. This record reports observations; the [hosting specification](docs/specs/backend-and-simulation.md#implementation-defaults-hosting) owns requirements. The earlier audit below supplies restart, firewall, maintenance and alert evidence; those disruptive checks were not repeated.

| Acceptance check | Result and evidence | Remaining work |
| --- | --- | --- |
| 1: Approved email-code entry | **Passed for the placeholder.** Existing approved Chrome session opened the built UI again; earlier email-code login and manual public health response are recorded above. | Fresh login by the non-author verifier. Automated `/health` navigation still reports `ERR_BLOCKED_BY_CLIENT`; no browser protection was disabled. |
| 1: Unapproved identity denied | **Inconclusive end to end.** Sole Allow rule includes only the approved UCF address; no Bypass/Service Auth rule. With explicit permission, submitted the maintainer's excluded Gmail identity: login displayed the generic code prompt, but no matching code was found in inbox/spam and no blocked authentication event was visible. The policy tester returned `invalid_user_id`, with zero policies evaluated; neither result is denial proof. | Obtain a verifiable excluded-identity decision; do not broaden the allowlist to make this test possible. |
| 1: Six-hour policy, hostname, maintainer and revision | **Passed configuration; revision qualification open.** Dashboard confirms whole hostname, One-time PIN, six hours, policy inheriting application duration, HttpOnly and binding enabled. Maintainer: Diab. Running tag: `hosting-20260928`, based on `d6b251632c8f1693f7ae8ad1404fdec2902e65f9` plus the hosting working tree. | KSAT-23 supplies immutable SHA images/GHCR publishing. The trial tag is not a tested immutable application release. |
| 2: Anonymous API/WebSocket denial | **Passed at the edge.** Public checker: 22 requests returned Access 302, including session GET, Attempt POST and HTTP/1.1 WebSocket upgrade, both anonymous and malformed header/cookie. | KSAT-12 → KSAT-23 supplies the real owned event stream; no 101/session exchange is claimed. |
| 2: Direct origin and alternate routes | **Passed for tested paths.** Ports 8000/8080 refused via Tailscale IPv4/IPv6 and VM LAN address; off-site public IPv6 timed out. Only loopback 8080 is listening. Local script/admin/docs routes return 404; public equivalents require Access. Live connector config has one hostname and final `http_status:404`. | Router policy/public IPv4 forwarding and physical recovery still need the home checks below. Loopback and SSH forwarding are trusted maintainer access, not JWT-protected application entrances. Player-container reachability waits for KSAT-11/12/23. |
| 2: JWT issuer/audience/signature/expiry | **Passed configuration and isolated validator cases; live fault injection untested.** Live cloudflared 2026.9.3 config has `access.required=true`, team `noisy-cherry-b0bc`, and the application's exact audience. Seven isolated cases exercise its actual constructor/handler: valid, missing, malformed, wrong issuer, wrong audience, wrong RSA signature and expired. | Fixture signing keys/JWKS are substituted only in the test process. These do not prove every fault through the running tunnel. Do not label a malformed public token as four independent live checks. |
| 2: Another browser cannot inspect/control an owned Attempt | **Blocked.** No session/Attempt routes or runtime exist. | KSAT-12 (Start/observe/Stop and ownership), packaged by KSAT-23; KSAT-11 supplies the runtime. |
| 3: Access expiry, reauthentication, no replay or inferred Attempt expiry | **Blocked.** No active feature session or reconnect client exists. | KSAT-12 and KSAT-31 (restore live session state), then KSAT-23 packaging. This acceptance stays in KSAT-24; KSAT-26 additionally covers dirty drafts and terminal reconnection after KSAT-13/14. |
| 3: Real build/runtime sizing | **Passed for scaffold only; Player capacity blocked.** Measurements below are from the actual HP VM. | KSAT-11/12 and KSAT-23 provide a packaged Player runtime; rerun with its limits, active workload, cleanup and memory-pressure behavior. KSAT-26 owns final three-Challenge capacity acceptance. |
| Focused checks, CI and non-author review | Local Python lint/test, TypeScript lint/test/build, live HTTP checks and isolated validator cases passed. All four [PR #2 CI jobs](https://github.com/kamillamamatova/knight-sat-sim/actions/runs/36466498114) passed, including real Compose build/protection checks and the pinned upstream validator fixture. Denzel (`denzel-galang`) was requested for non-author review. | Non-author approval/setup verification remains open; neither the prior host-decision sign-off nor an agent review satisfies this. Diab reran the deployed privileged checker successfully after private authentication at 14:45 EDT; evidence is recorded below. |

The VM reports 2 vCPUs, 3,848 MiB total RAM (3,215 MiB available at the initial sample), 3,847 MiB unused host swap, and a 39 GiB root filesystem with 8.4 GiB used/28 GiB available. The earlier no-cache image build log `/var/log/knightsat-image-refresh-20260928.log` records `npm ci` 9.2 s and the TypeScript/Vite build step 5.1 s (Vite 1.61 s), producing 222.79 kB JavaScript/69.44 kB gzip. These are individual build-step durations, not total elapsed time or peak build memory. Both image builds completed; build-peak memory was not recorded.

Read-only live cgroup counters during this audit: server 81,670,144 bytes current / 96,014,336 peak, capped at 805,306,368 bytes, 1 CPU and 128 tasks; Nginx 11,456,512 current / 16,568,320 peak, capped at 134,217,728 bytes, 0.25 CPU and 64 tasks. Both have zero additional swap allowance and zero OOM/OOM-kill events. Counts were 7 server tasks/3 Nginx tasks. Peaks are since these container cgroups started, not Player-workload measurements. No Player runtime was present or stressed.

Diab’s terminal screenshot at **14:45 EDT on 2026-09-28** confirms the deployed `sudo python3 deploy/check-hosting.py` passed UI/SPA routing, health/API proxy, restricted paths, non-root/read-only containers, resource limits, private ports and restart-policy checks. This reran the existing deployed checker, not the enhanced PR checker, and did not restart services. The following `docker stats --no-stream` sample reported web **10.34 MiB / 128 MiB, 0.00% CPU, 3 PIDs** and server **69.99 MiB / 768 MiB, 2.72% CPU, 12 PIDs**. Docker listed web images at **81.8 MB** and server images at **222 MB** for both `hosting-20260928` and `hosting-maint-20260928`. These are point-in-time placeholder measurements; Docker memory accounting differs from the raw cgroup counters above. This closes the pending private-sudo verification, not the Player capacity or non-author review checks.

SHA-256 comparisons matched live/local Compose, Dockerfile, Nginx, both dependency locks, `server/api/main.py` and `ui/src/App.tsx`. The improved checker and validator fixture are review artifacts; they do not replace the running application. No service restart, Access-policy weakening, paid service or backup system was introduced by this audit.

To reproduce the isolated JWT checks with Go 1.26, use a temporary checkout of `cloudflare/cloudflared` at commit `96d39adbc812dc7363834bda908970c1a2560a72` (2026.9.3), copy `deploy/cloudflared-jwt_test.go` into its `ingress/middleware/` directory, and run `go test ./ingress/middleware -run TestKnightSatJWT -v`. CI does the same. [Cloudflare documents connector validation](https://developers.cloudflare.com/cloudflare-one/access-controls/applications/http-apps/authorization-cookie/validating-json/); the fixture tests the [versioned implementation](https://github.com/cloudflare/cloudflared/blob/96d39adbc812dc7363834bda908970c1a2560a72/ingress/middleware/jwtvalidator.go), not a replacement validator in our application.

### Hosting audit and maintenance

Remote audit on **2026-09-28**:

- Enabled **HTTP Only** and **Enable Binding Cookie** for the Knight Sat Sim Access application; reopened its settings to verify both persisted. The whole-hostname destination, `di227923@ucf.edu` allowlist, One-time PIN, six-hour session, and connector JWT audience/team validation remain in place. Signed-in Chrome still reached the placeholder UI, and `python3 deploy/check-hosting.py --public` passed after the change. Binding is appropriate for this browser application; SSH uses Tailscale separately and Cloudflare One Client authentication is off. See [Cloudflare's cookie compatibility notes](https://developers.cloudflare.com/cloudflare-one/access-controls/applications/http-apps/authorization-cookie/) before adding integrations.
- Created **Knight Sat Sim tunnel health**, a free Tunnel Health email alert to the confirmed Cloudflare account email. It selects only tunnel `5c4c16a7-d89d-4d90-83b2-6bac5584e2c3`, includes healthy/degraded/down transitions, and excludes future tunnels. The saved alert is enabled. Test-email delivery was confirmed by Diab’s Gmail screenshot on 2026-09-28; its placeholder `tunnel-name`, sample ID and 2022 event date identify sample data, not a real Knight Sat outage. Manage it under **Manage account → Alerts**. [Tunnel alerts](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/monitor-tunnels/notifications/) detect connector failures, not a broken Nginx/backend, failed `/health`, or login problems. No paid application-health monitoring was added.
- Tailscale SSH connected successfully from the travelling Mac. Device expiry is **2027-03-27 13:56:17 UTC**; reauthenticate before then and verify a fresh connection. Four tunnel connections were healthy, reported request errors were zero, local `/health` returned `{"status":"ok"}`, and systemd reported no failed units. SSH, Tailscale, Docker and cloudflared are enabled for startup. IPv6 remains enabled.
- Resolved the `/health` hosting concern: automated Chrome navigation reproduced `ERR_BLOCKED_BY_CLIENT`, but Diab’s manual signed-in Chrome screenshot at 14:10 on 2026-09-28 shows `{"status":"ok"}` at the public `/health` URL. Local health and signed-in UI also passed. The failure was specific to the automated browser path; its exact blocking component was not identified. No Access setting or browser protection was disabled to make the check pass.
- Privileged inspection and `sudo python3 /opt/knightsat/deploy/check-hosting.py` passed after private authentication. Both containers are non-root, unprivileged, read-only, drop all capabilities, forbid privilege escalation, and restart unless stopped. Server limits are 1 CPU / 768 MiB / 128 processes; web limits are 0.25 CPU / 128 MiB / 64 processes, with no additional swap allowance and bounded local logs (3 × 10 MiB each). Only web publishes a port, on `127.0.0.1:8080`; metrics remain on `127.0.0.1:20241`. The server joins only the internal backend network; web joins frontend and backend. Neither mounts the Docker socket. The named `knightsat_progress` volume is mounted at `/data`, owned by numeric UID/GID 10001, and currently empty; it is not evidence of implemented Challenge persistence. `/etc/cloudflared` is root-owned mode 0700 and its token is root-owned mode 0600; token contents were not read.
- Enabled UFW for IPv4 and IPv6 with default-deny incoming/routed traffic and allowed outgoing traffic. SSH is allowed on `tailscale0` for both families; the home fallback allows TCP 22 on `enp6s18` from/to `192.168.1.0/24`, plus IPv6 link-local from/to `fe80::/10` on that interface. Globally addressed IPv6 SSH is not allowed. OpenSSH remains key-only for `diab`, with root/password/keyboard-interactive login disabled. Its socket still listens on both families: ingress rules enforce the restriction without binding startup to a DHCP address or Tailscale availability. IPv6 itself remains enabled, including neighbor discovery and router advertisements.
- Before firewall changes, saved the original UFW configuration and effective IPv4/IPv6 rules under `/root/knightsat-firewall-rollback-20260928` and armed a ten-minute systemd rollback. Cancelled it only after fresh independent SSH connections, origin checks and the public Access check passed. Fresh Tailscale IPv4 and IPv6 SSH succeeded; an outside TCP 22 probe to the VM’s public IPv6 timed out (this alone does not identify whether the router or VM dropped it). Signed-in Chrome still loaded the UI. Verified the rollback service never ran and UFW remains active/enabled. Docker forwarding/NAT/isolation and Tailscale chains remain intact; Tailscale accepts authenticated tailnet traffic before UFW. Keep application ports on loopback: Docker-published ports can bypass UFW.
- Explicitly disabled automatic reboots in `/etc/apt/apt.conf.d/52knightsat-maintenance`. `/etc/needrestart/conf.d/knightsat.conf` excludes `docker`, `containerd`, `tailscaled`, `cloudflared` and `ssh` services from automatic library-triggered restarts. Ubuntu unattended security upgrades remain enabled. Changed Tailscale from automatic installation to check-only (`tailscale set --auto-update=false`); verified `Check=true`, `Apply=false`. Package maintainer scripts can still restart their own services, so third-party package installation remains attended. `needrestart -b -r l` reported no pending service or kernel restart.

Rebuilt the same VM source and lockfiles with `--pull --no-cache` as `hosting-maint-20260928`. Both refreshed images passed isolated Compose startup/health checks and served the UI and health API on `127.0.0.1:18081`. Sorted OS-package inventories matched the running images exactly; no production replacement was necessary. The temporary test containers, networks and empty test volume were removed; the real stack and `knightsat_progress` were untouched. Retained the refreshed image tags and `/var/log/knightsat-image-refresh-20260928.log` as maintenance evidence. This validates image refresh, not the future application deployment workflow or a vulnerability scan.

Diab owns a **weekly maintenance review**, plus an immediate review after relevant security advisories. Keep it separate from the planned **Update website** workflow. Ubuntu unattended upgrades currently cover Ubuntu security origins, not the official Docker, Tailscale or cloudflared repositories. Review the [Ubuntu restart behavior](https://ubuntu.com/server/docs/how-to/software/automatic-updates/) when changing that policy: Ubuntu 24.04's `needrestart` may restart services after library updates.

1. Refresh package lists with `sudo apt-get update`; inspect `apt list --upgradable` and `apt-cache policy docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin tailscale cloudflared`. Review vendor release/security notes before changing major versions. After a successful privileged `apt-get update` on 2026-09-28, there were no pending upgrades: Docker Engine/CLI 29.8.1, containerd 2.3.6, Buildx 0.37.1, Compose 5.5.1, Tailscale 1.102.4 and cloudflared 2026.9.3. Installed and candidate versions matched; no package installation or reboot was required.
2. For any selected package update, first use `sudo apt-get -s install --only-upgrade PACKAGE` to inspect the transaction. Install only reviewed packages in an attended maintenance window. Package maintainer scripts can restart their own services even if `needrestart` is configured to defer restarts. Tailscale updates can interrupt remote management; arrange console recovery or perform them at home if recovery is uncertain. Check `/var/run/reboot-required` and defer any reboot to that window.
3. Review container base images as well as host packages: host APT updates do not patch software inside existing images. From the exact checked source revision, build a new revision tag with `sudo env REVISION=NEW_UNIQUE_TAG docker compose -f compose.hosting.yml build --pull --no-cache`. This refreshes base layers and OS packages while retaining locked application dependencies. Retain the running image tags until validation succeeds. Review dependency advisories separately; lockfile changes require ordinary code review and CI. Do not run automatic image updaters or prune the progress volume.
4. The current scaffold has no Player sessions. Once sessions exist, do not recreate containers or restart Docker/the VM until the specified atomic admission closure and persistent maintenance state are available and the Platform is idle. An informal user-count check is not sufficient. KSAT-25 owns that mechanism; this maintenance procedure does not implement or bypass it.
5. After an approved replacement/restart, run the VM checker with sudo, the public checker from outside, a fresh `ssh knightsat`, and a signed-in browser check. Check container health, retained storage, tunnel connections and failed systemd units; record versions and results here. Confirm `apt-config dump` still reports `Unattended-Upgrade::Automatic-Reboot "false"`, review `sudo needrestart -b -r l`, and check the hosting restart exclusions before relying on them after OS upgrades.

### Checks that still need home access

- Verify the router's unsolicited IPv4 **and IPv6** ingress policy, no SSH/Proxmox forwards or UPnP mappings, and remote administration disabled. Reserve `192.168.1.52` for `BC:24:11:DB:1E:3D`. The router responded from the VM, but its authenticated settings were not available; reachability does not establish firewall protection or a DHCP reservation.
- Verify Proxmox datacenter/node/VM firewall settings and VM 100's startup/shutdown order through the existing private console. Its HTTPS service was reachable from the VM but certificate verification failed; no authenticated settings were inspected and no administration route was opened.
- Confirm HP BIOS **restore power after AC loss**, Proxmox startup, VM automatic startup, and recovery of router/internet, SSH, tunnel and application after a controlled physical power-loss test. A previously successful guest reboot does not prove physical recovery. Perform this attended, with no Player session and with the accepted risk that backups remain deferred.
- Test `ssh knightsat-lan` and recovery through the Proxmox console after the firewall changes. Do not restore `base-ubuntu-docker` casually: it predates remote access and discards later guest changes. Preserve working private console credentials in a password manager.

## Tests and lint

```bash
# server
cd server && uv sync --extra dev && uv run ruff check . && uv run pytest

# ui
cd ui && npm ci && npm run lint && npm test
```

Pull requests run the same checks in GitHub Actions.

## How we work

Jira holds build tickets. Open a branch named with the Jira key, open a pull request whose title starts with that key, wait for CI, and get one teammate review before merge. Details: [`CONTRIBUTING.md`](CONTRIBUTING.md).


## Update website: operator runbook

The workflow is implemented for the **placeholder only**. Deployment setup and the first live workflow run must be verified before calling it operational. Its host-pinned fingerprint refuses any change to application/build inputs. Finish KSAT-12/16/23/25 session, controller, migration and admission integration before deploying Player features. Application development and CI can proceed meanwhile.

### One-time private setup

1. A repository administrator creates GitHub Environment **production**, with custom deployment branches allowing only the branch `main` (no tags). Keep existing repository protections. Store only `DEPLOY_SSH_KEY` as an environment secret; variables are `DEPLOY_HOST_KEY`, `TS_CLIENT_ID`, `TS_AUDIENCE`. Pin `DEPLOY_HOST_KEY` to the VM's independently verified Ed25519 key as `100.108.206.107 ssh-ed25519 …`; never use runtime `ssh-keyscan` as trust establishment.
2. In the existing **Free** Tailscale account, define `tag:knightsat-deploy` owned by the maintainer and a grant from that tag to **100.108.206.107 TCP 22 only**. Ensure no wildcard grant gives this tag wider access; preserve existing human access. Configure [OIDC trust](https://tailscale.com/docs/features/workload-identity-federation) for issuer `https://token.actions.githubusercontent.com`, subject `repo:senior-design-organization@335218082/knights-sat-sim@1393975003:environment:production`, and exact claims `ref=refs/heads/main`, `workflow_ref=senior-design-organization/knights-sat-sim/.github/workflows/update-website.yml@refs/heads/main`, `event_name=workflow_dispatch`. This repository uses GitHub’s immutable subject format: retain both numeric IDs and verify the exact subject if moving or recreating the repository. Grant only auth-key creation for this tag, not policy/user administration. Copy its nonsecret client ID and audience to the environment variables. The official action removes its ephemeral device after the run. Check runner denial to unrelated tailnet devices before live deployment.
3. Generate a dedicated Ed25519 deployment key outside this repository. Transfer its private half directly into the environment secret without printing it. Keep the maintainer's personal SSH key separate. On the VM, stage the independently reviewed source and public half only. Privately authenticate sudo and run `sudo python3 /path/to/reviewed-source/deploy/install.py /path/to/deploy-key.pub`. The installer checks the historical placeholder, installs root-owned code/Compose/fingerprint, and creates a restricted forced-command identity. It does not replace containers or remove the progress volume. Inspect ownership, sudoers and the key restriction before use. If SSH uses an `AllowUsers` list, include `knightsat-deploy` alongside the maintainer, validate with `sshd -t`, and reload SSH. Verify this key forces the deployment validator even when a shell command is requested. Installation is one-time; it refuses an existing qualification record.
4. Main push CI must pass all four original jobs and **Publish revision images**. That job smoke-tests the actual images before publishing, uses a unique `<SHA>-<run-ID>-<attempt>` tag for each tested build, and uploads the digest manifest as the `release-<attempt>` artifact (90 days). Private GHCR images are pulled with the short-lived workflow token; no host PAT is needed. Use only free standard runners for this public repository and current [GHCR free image storage/bandwidth](https://docs.github.com/en/packages/learn-github-packages/introduction-to-github-packages). Do not enable paid usage to resolve a failure.

### Routine update

Open **Actions → Update website → Run workflow** on `main`, and paste the complete 40-character SHA of a successful main push run. The selected SHA may be behind main but must be its ancestor and have unchanged qualified build inputs. Both workflow and host verify main membership, latest exact-SHA CI success, all required job results, unexpired run artifact and image identities. GHCR digests, never moving tags, drive replacement. Two workflow runs queue without cancellation; the host also refuses overlap.

A successful run prints `DEPLOYED: <SHA>`, links its qualifying CI run, and verifies the origin revision/health, container protections, retained `knightsat_progress` volume and anonymous/malformed Access denial (including a WebSocket upgrade). `/revision` is behind the unchanged whole-hostname Access policy. Signed-in teammates can read it; maintainers can also use the private origin. Inspect `sudo cat /opt/knightsat/current.json` for the exact image IDs and CI link. The public checker proves edge denial, not a functional application WebSocket or live JWT fault injection.

### Failure and attended recovery

A rejected SHA, failed check, missing artifact, pull failure or changed bootstrap input stops before replacement. The current site keeps running. Retry only after resolving the reported cause; rerunning main CI builds/tests a fresh uniquely tagged image pair and renews the artifact. A selected deployment still uses only the recorded immutable digests.

The one-time transition from `hosting-20260928` has a bounded exception: its historical Nginx image has no marker support. Until the new web container starts, it can still show the old placeholder or a connection error. There are no Player sessions; the host marker still blocks another deployment. Do not restore that historical image and claim maintenance protection. If this first transition fails, repair forward to the selected qualified digest pair.

After replacement begins, failures retain `/opt/knightsat/deploy/state/active`; Nginx serves maintenance and a second update refuses. Connect with `ssh knightsat`, inspect `deploy/state/pending.json`, `current.json`, `.env`, container state and logs. The pending record includes selected digests and previous image IDs; records contain no credential. Do not delete the volume or blindly roll back a database schema.

For this frozen placeholder only, with the root cause understood, acquire the same exclusive lock in an attended sudo shell (`flock -n /opt/knightsat/update.lock bash`). Keep the marker. Recreate using explicitly verified pending digest references and the same Compose file/project and volume, or deliberately restore a previously qualified, marker-aware digest pair if it is still available. The historical trial image is not such a recovery target. Set `REVISION`, `SERVER_IMAGE`, `WEB_IMAGE`, and `STATE_DIR=/opt/knightsat/deploy/state` consistently. Run `python3 deploy/check-hosting.py --maintenance`, the public checker, verify `/revision`, both container image IDs and health, then update `.env` and `current.json` to the actual healthy release. Only then remove `deploy/state/active` and confirm `python3 deploy/check-hosting.py` passes. Exit the locked shell. If any check fails, retain maintenance and investigate. Once application schemas exist, this bootstrap procedure is prohibited until the full admission/migration recovery contract replaces it.

Local checks: `python3 deploy/test_release.py`, `python3 deploy/test_check_hosting.py`, and the normal Compose hosting smoke check. The unit fixtures prove refusal and failure ordering without touching the VM; container maintenance/restart/volume checks provide separate evidence. None proves session busy refusal or migration safety.

## Local Player runtime checks (KSAT-11)

The isolated runtime controller is available to server code; browser Start/Stop and
production Sim wiring remain KSAT-12. The default development and hosted services
still serve the scaffold. This harness uses **local Docker only** and does not
change the hosted demo or its deployment fingerprint.

```bash
docker build -t knightsat-player:ksat11 player
docker compose -p ksat11-test -f compose.runtime-test.yml build
docker compose -p ksat11-test -f compose.runtime-test.yml run --rm runtime-tests
# Remove only the disposable harness volumes/network after the tests finish:
docker compose -p ksat11-test -f compose.runtime-test.yml down -v
```

Run one behavior by appending `pytest tests/runtime/test_controller.py -k <name> -v`
to the `run --rm runtime-tests` command. Run the harness serially: its three named
volumes belong to one test deployment. The trusted test server has the local Docker
socket; the Player never receives it. The test image uses the server lockfile.
Ordinary `uv run --extra dev pytest` skips real-container checks without the harness
environment; CI runs them in a dedicated required-for-publishing job. Typecheck with
`uv run --extra dev mypy --ignore-missing-imports api` from `server/`.

The harness's three deployment-labelled named volumes are bounded tmpfs and remain
mounted in the trusted server throughout each test. Runtime replacement preserves
authored contents. Session cleanup empties personal data and removes execution,
including detached processes, temporary/home files and the PTY. Empty infrastructure
volumes remain attached until `down -v`; they contain no retained personal data.
Do not use a broad Docker prune command. If a test process is killed, inspect only
containers with `org.knightsat.deployment=ksat11-test`, record their runtime labels,
and deliberately remove those identified test containers before removing the
harness volumes. A failed cleanup must not be treated as successful admission.

Local evidence, 2026-09-29 UTC: Docker Desktop 4.93.0, Engine 29.8.1,
Linux ARM64, 10 CPUs / approximately 7.75 GiB Docker VM memory. Real Player probes
verified UID/GID 1000, network none, read-only root/resources, dropped capabilities,
no-new-privileges and 0.5 CPU / 128 MiB / no extra swap / 64 processes / 256 descriptors.
Observed exhaustion: authored/tmp/home writes stopped at 67,108,864 / 16,777,216 /
4,194,304 bytes; managed and bridge storage rejected writes beyond 1 MiB; process
creation and descriptor opens hit kernel limits; CPU throttling occurred; an
unbounded allocator was killed with status 137. Exact available child/descriptor
counts include the shell and bridge overhead, so they may vary.

The checks also cover retained authored files, fresh read-only managed context,
non-overwriting/symlink-safe provisioning, quota-failure recovery, detached-child
removal, failed/lost Docker responses, cancellation during creation, abandoned
runtime refusal, foreign-resource preservation, denied IPv4/IPv6 egress/private
paths, direct-socket and loopback authentication, denied non-script routes, revoked
queued traffic, receive routing and the 256-byte input bound. Bridge fixtures
prove infrastructure transport only; they do not claim Sim/Link completion or
receiver readiness. No browser journey or HP x86-64 hosted capacity was tested here.

Final local verification: all 20 server tests passed with real Docker, plus the UI
test/build, Python/TypeScript type checks, lint and five deployment-tool regression
checks. Standards and spec reviews found no remaining issues after the close-race
and cleanup-fault regressions were added.

KSAT-12 supplies real Sim handlers, browser ownership and the shared lifecycle lock;
KSAT-37 supplies startup reconciliation, maintenance and readiness. KSAT-13 drains
the existing PTY into its bounded terminal buffers. KSAT-17/20 extend
`player/python/kss_client.py` and provide the authored starter/managed scenario bytes;
this image currently supplies `load_connection()` and pinned `websockets`, not a
PING solver or completed recording. See the controller handoff in the
[Workspace spec](docs/specs/terminal-workspace.md#controller-integration-handoff).
