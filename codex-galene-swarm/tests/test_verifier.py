from __future__ import annotations

import io
import tarfile
import tempfile
import unittest
from pathlib import Path
import subprocess

from codex_galene_swarm.models import TaskContract
from codex_galene_swarm.verifier import DockerVerifier, VerificationError


PATCH = """diff --git a/example.py b/example.py
index 7898192..422c2b7 100644
--- a/example.py
+++ b/example.py
@@ -1 +1 @@
-print('old')
+print('new')
"""


class FakeExecResult:
    exit_code = 0
    output = b"verification passed\n"


class FakeContainer:
    def __init__(self, staging: bool = False) -> None:
        self.staging = staging
        self.started = False
        self.removed = False
        self.archive = b""
        self.exec_arguments = None

    def start(self) -> None:
        self.started = True

    def put_archive(self, path: str, archive: bytes) -> bool:
        self.archive = archive
        return path == "/"

    def exec_run(self, command, **kwargs):
        self.exec_arguments = (command, kwargs)
        if command == ["test", "-f", "/workspace/.swarm-ready"]:
            return FakeExecResult()
        return FakeExecResult()

    def reload(self) -> None:
        self.status = "running"

    def commit(self, **kwargs):
        self.commit_arguments = kwargs
        return FakeImage()

    def remove(self, force: bool = False) -> None:
        self.removed = force


class FakeContainers:
    def __init__(self) -> None:
        self.created = []

    def create(self, image: str, **kwargs):
        container = FakeContainer(staging=not self.created)
        self.created.append(({"image": image, **kwargs}, container))
        return container


class FakeImage:
    id = "sha256:snapshot"


class FakeImages:
    def __init__(self) -> None:
        self.removed = []

    def remove(self, image: str, force: bool = False) -> None:
        self.removed.append((image, force))


class FakeClient:
    def __init__(self) -> None:
        self.containers = FakeContainers()
        self.images = FakeImages()


class DockerVerifierTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.repository = Path(self.temp.name)
        (self.repository / "example.py").write_text("print('old')\n", encoding="utf-8")
        subprocess.run(["git", "init", "-q"], cwd=self.repository, check=True)
        subprocess.run(["git", "add", "example.py"], cwd=self.repository, check=True)
        self.client = FakeClient()
        self.verifier = DockerVerifier(str(self.repository), "project-tests:local", client=self.client)

    def tearDown(self) -> None:
        self.temp.cleanup()

    @staticmethod
    def contract(allowed_files=None) -> TaskContract:
        return TaskContract.from_dict({
            "task_id": "verify",
            "role": "implementer",
            "objective": "Update example",
            "allowed_files": allowed_files or ["example.py"],
            "verification_command": ["python", "example.py"],
        })

    def test_runs_in_hardened_networkless_container_and_removes_it(self) -> None:
        result = self.verifier.verify(self.contract(), PATCH)
        stage_options, stager = self.client.containers.created[0]
        options, container = self.client.containers.created[1]
        self.assertEqual("passed", result.status)
        self.assertTrue(result.network_disabled)
        self.assertTrue(options["network_disabled"])
        self.assertTrue(options["read_only"])
        self.assertEqual(["ALL"], options["cap_drop"])
        self.assertIn("no-new-privileges", options["security_opt"])
        self.assertEqual("65534:65534", options["user"])
        self.assertFalse(stage_options["read_only"])
        self.assertTrue(stager.removed)
        self.assertTrue(container.removed)
        self.assertEqual([("sha256:snapshot", True)], self.client.images.removed)
        command, exec_options = container.exec_arguments
        self.assertEqual(["python", "example.py"], command)
        self.assertEqual("/workspace", exec_options["workdir"])

        with tarfile.open(fileobj=io.BytesIO(stager.archive)) as archive:
            content = archive.extractfile("snapshot/example.py").read().decode("utf-8")
        self.assertEqual("print('new')\n", content)

    def test_rejects_changes_outside_allowed_files_before_docker(self) -> None:
        with self.assertRaisesRegex(VerificationError, "outside allowed_files"):
            self.verifier.verify(self.contract(["different.py"]), PATCH)
        self.assertEqual([], self.client.containers.created)

    def test_contract_rejects_executable_check_without_allowed_files(self) -> None:
        with self.assertRaisesRegex(ValueError, "requires allowed_files"):
            TaskContract.from_dict({
                "task_id": "verify",
                "role": "implementer",
                "objective": "Update example",
                "verification_command": ["python", "example.py"],
            })

    def test_contract_rejects_unbounded_verification_command(self) -> None:
        with self.assertRaisesRegex(ValueError, "bounded command size"):
            TaskContract.from_dict({
                "task_id": "verify",
                "role": "implementer",
                "objective": "Update example",
                "allowed_files": ["example.py"],
                "verification_command": ["x" * 4097],
            })

    def test_repository_copy_excludes_ignored_files(self) -> None:
        (self.repository / ".gitignore").write_text(".env\n", encoding="utf-8")
        (self.repository / ".env").write_text("SECRET=do-not-copy\n", encoding="utf-8")
        subprocess.run(["git", "add", ".gitignore"], cwd=self.repository, check=True)
        self.verifier.verify(self.contract(), PATCH)
        stager = self.client.containers.created[0][1]
        with tarfile.open(fileobj=io.BytesIO(stager.archive)) as archive:
            names = archive.getnames()
        self.assertNotIn("snapshot/.env", names)
        self.assertIn("snapshot/.gitignore", names)


if __name__ == "__main__":
    unittest.main()
