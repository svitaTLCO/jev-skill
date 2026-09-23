from __future__ import annotations

import io
import os
import shutil
import subprocess
import tarfile
import tempfile
import time
import uuid
from pathlib import Path, PurePosixPath
from typing import Protocol

import docker
from docker.errors import APIError, DockerException, ImageNotFound

from .models import TaskContract, VerificationResult


class VerificationError(RuntimeError):
    """The verifier infrastructure could not safely execute a candidate."""


class CandidateVerifier(Protocol):
    def verify(self, contract: TaskContract, candidate: str) -> VerificationResult: ...


class DockerVerifier:
    """Apply a bounded diff, then test it in an ephemeral networkless container."""

    OUTPUT_LIMIT = 32_000

    def __init__(
        self,
        repository_path: str,
        image: str,
        timeout_seconds: int = 300,
        client: docker.DockerClient | None = None,
    ) -> None:
        repository = Path(repository_path).resolve()
        if not repository.is_dir():
            raise ValueError(f"Repository path does not exist: {repository}")
        if not image.strip():
            raise ValueError("Verifier image is required")
        if not 1 <= timeout_seconds <= 1800:
            raise ValueError("Verifier timeout must be between 1 and 1800 seconds")
        self.repository = repository
        self.image = image.strip()
        self.timeout_seconds = timeout_seconds
        self.client = client or docker.from_env()

    def verify(self, contract: TaskContract, candidate: str) -> VerificationResult:
        if not contract.verification_command:
            raise VerificationError("Task has no verification command")
        if not candidate.strip():
            raise VerificationError("Candidate diff is empty")

        started = time.perf_counter()
        container = None
        stager = None
        snapshot = None
        with tempfile.TemporaryDirectory(prefix="swarm-verify-") as temp:
            workspace = Path(temp) / "workspace"
            self._copy_repository(workspace)
            self._apply_candidate(workspace, contract, candidate)
            archive = self._archive(workspace)
            name = f"swarm-verify-{uuid.uuid4().hex[:12]}"
            try:
                common_limits = {
                    "network_disabled": True,
                    "cap_drop": ["ALL"],
                    "security_opt": ["no-new-privileges"],
                    "pids_limit": 256,
                    "mem_limit": "512m",
                    "nano_cpus": 1_000_000_000,
                    "user": "65534:65534",
                    "detach": True,
                }
                stager = self.client.containers.create(
                    self.image,
                    name=f"{name}-stage",
                    command=["sleep", str(self.timeout_seconds + 30)],
                    entrypoint=[],
                    read_only=False,
                    **common_limits,
                )
                stager.start()
                if not stager.put_archive("/", archive):
                    raise VerificationError("Docker rejected the repository archive")
                snapshot = stager.commit(repository="swarm-verifier-snapshot", tag=name)
                stager.remove(force=True)
                stager = None

                container = self.client.containers.create(
                    snapshot.id,
                    name=name,
                    command=[
                        "sh", "-c",
                        "cp -a /snapshot/. /workspace && touch /workspace/.swarm-ready && exec sleep \"$1\"",
                        "swarm-init", str(self.timeout_seconds + 30),
                    ],
                    entrypoint=[],
                    read_only=True,
                    tmpfs={
                        "/workspace": "rw,exec,nosuid,nodev,size=256m,mode=0755,uid=65534,gid=65534",
                        "/tmp": "rw,noexec,nosuid,nodev,size=64m,mode=1777",
                    },
                    working_dir="/workspace",
                    environment={"HOME": "/tmp", "PYTHONDONTWRITEBYTECODE": "1"},
                    **common_limits,
                )
                container.start()
                self._wait_until_ready(container)
                result = container.exec_run(
                    contract.verification_command,
                    workdir="/workspace",
                    user="65534:65534",
                    demux=False,
                )
                output = (result.output or b"").decode("utf-8", errors="replace")
                output = output[-self.OUTPUT_LIMIT :]
                status = "passed" if result.exit_code == 0 else "rejected"
                return VerificationResult(
                    status=status,
                    image=self.image,
                    command=contract.verification_command,
                    exit_code=result.exit_code,
                    duration_ms=round((time.perf_counter() - started) * 1000, 3),
                    output=output,
                )
            except (APIError, DockerException, ImageNotFound) as exc:
                raise VerificationError(f"Docker verifier failed: {str(exc)[:400]}") from exc
            finally:
                if container is not None:
                    try:
                        container.remove(force=True)
                    except DockerException:
                        pass
                if stager is not None:
                    try:
                        stager.remove(force=True)
                    except DockerException:
                        pass
                if snapshot is not None:
                    try:
                        self.client.images.remove(snapshot.id, force=True)
                    except DockerException:
                        pass

    def _wait_until_ready(self, container) -> None:
        for _ in range(100):
            probe = container.exec_run(["test", "-f", "/workspace/.swarm-ready"])
            if probe.exit_code == 0:
                return
            container.reload()
            if container.status in {"exited", "dead"}:
                raise VerificationError("Verifier container exited while preparing its workspace")
            time.sleep(0.05)
        raise VerificationError("Verifier workspace preparation timed out")

    def _copy_repository(self, destination: Path) -> None:
        process = subprocess.run(
            [
                "git", "-c", f"safe.directory={self.repository}",
                "ls-files", "-z", "--cached", "--others", "--exclude-standard",
            ],
            cwd=self.repository,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if process.returncode != 0:
            error = process.stderr.decode("utf-8", errors="replace")
            raise VerificationError(f"Repository file inventory failed: {error[:400]}")
        destination.mkdir()
        for raw_path in process.stdout.split(b"\0"):
            if not raw_path:
                continue
            relative = self._safe_relative(raw_path.decode("utf-8", errors="strict"))
            source = self.repository / relative
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            if source.is_symlink():
                target.symlink_to(os.readlink(source))
            elif source.is_file():
                shutil.copy2(source, target)
            else:
                raise VerificationError(f"Unsupported repository entry: {relative!r}")

    def _apply_candidate(self, workspace: Path, contract: TaskContract, candidate: str) -> None:
        patch_path = workspace.parent / "candidate.diff"
        patch_path.write_text(candidate, encoding="utf-8")
        changed_files = self._changed_files(patch_path, workspace)
        allowed = {self._safe_relative(path) for path in contract.allowed_files}
        unexpected = changed_files - allowed
        if unexpected:
            raise VerificationError(f"Candidate modifies files outside allowed_files: {sorted(unexpected)}")
        if not changed_files:
            raise VerificationError("Candidate diff does not modify any files")
        self._git_apply(workspace, ["--check", "--whitespace=error-all", str(patch_path)])
        self._git_apply(workspace, ["--whitespace=error-all", str(patch_path)])

    def _changed_files(self, patch_path: Path, workspace: Path) -> set[str]:
        process = subprocess.run(
            ["git", "apply", "--numstat", "-z", str(patch_path)],
            cwd=workspace,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if process.returncode != 0:
            error = process.stderr.decode("utf-8", errors="replace")
            raise VerificationError(f"Candidate is not a valid unified diff: {error[:400]}")
        records = process.stdout.split(b"\0")
        changed: set[str] = set()
        for record in records:
            if not record:
                continue
            parts = record.decode("utf-8", errors="strict").split("\t", 2)
            if len(parts) != 3:
                raise VerificationError("Candidate contains an unsupported diff record")
            changed.add(self._safe_relative(parts[2]))
        return changed

    @staticmethod
    def _safe_relative(value: str) -> str:
        path = PurePosixPath(value)
        if path.is_absolute() or not path.parts or ".." in path.parts:
            raise VerificationError(f"Unsafe repository path: {value!r}")
        return path.as_posix()

    @staticmethod
    def _git_apply(workspace: Path, arguments: list[str]) -> None:
        process = subprocess.run(
            ["git", "apply", *arguments],
            cwd=workspace,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if process.returncode != 0:
            error = process.stderr.decode("utf-8", errors="replace")
            raise VerificationError(f"Candidate diff cannot be applied: {error[:400]}")

    @staticmethod
    def _archive(workspace: Path) -> bytes:
        stream = io.BytesIO()
        with tarfile.open(fileobj=stream, mode="w") as archive:
            for path in workspace.rglob("*"):
                relative = path.relative_to(workspace)
                info = archive.gettarinfo(str(path), arcname=f"snapshot/{relative.as_posix()}")
                info.uid = 65534
                info.gid = 65534
                info.uname = "nobody"
                info.gname = "nogroup"
                if path.is_file():
                    with path.open("rb") as handle:
                        archive.addfile(info, handle)
                else:
                    archive.addfile(info)
        stream.seek(0)
        return stream.read()
