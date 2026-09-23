# Team release bundle: Linux and WSL

This directory is the source for the first image-only team bundle. Copy only
this directory to a developer's machine after an approved image has been
published to the internal registry. No source checkout or host Python is needed.

1. Copy `.env.example` to `.env`, set mode `0600`, and replace the image digest,
   endpoint, and credentials with approved values. Do not commit or share `.env`.
2. Authenticate Docker to the internal registry using the team's normal method.
3. From this directory, run `rtk docker compose pull server`. The image must be
   pinned by digest in `SWARM_IMAGE`.
4. Add this MCP server to Codex, replacing the path with this directory's
   absolute path:

   ```toml
   [mcp_servers.galene_swarm]
   command = "docker"
   args = ["compose", "--env-file", "/absolute/path/to/release/.env", "-f", "/absolute/path/to/release/docker-compose.yml", "run", "--rm", "-T", "server"]
   ```

The Compose project owns the `codex-galene-swarm-team_team-ledger` local Docker
volume. It survives container replacement and image upgrades. The service
requires Jev for every run even if a Codex call omits `require_jev`.

For an upgrade, save the current digest, update `SWARM_IMAGE`, pull, and restart
Codex's MCP connection. For rollback, restore the previous digest and restart.
Do not delete the ledger volume as part of upgrade or rollback. A future schema
migration may require a version-specific rollback procedure; verify release
notes before crossing such a version.

Run `rtk docker compose run --rm -T server` directly only for diagnostics; it uses
MCP stdio and may wait for client input. Missing keys or an unwritable ledger
fail at startup. A live `swarm_start` is needed to establish endpoint and model
route availability. Provider errors retain safe status metadata in task evidence.

Uninstalling the Codex MCP entry and image leaves the ledger intact. Deleting
the volume removes stored contracts, candidate text, and evidence permanently;
follow the team's retention decision before doing that.
