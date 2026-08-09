"""SSH remote execution HPC connector.

Supports two modes:
- SLURM-aware: detects remote SLURM and uses sbatch
- Plain nohup: falls back to nohup bash for non-SLURM hosts
"""

import json
import os
import posixpath
import re
import shlex
import subprocess
from pathlib import Path

from .base import BaseHPCConnector
try:  # Supports both MCP script loading and package-based test imports.
    from transfer import normalize_target, remote_manifest, validate_remote_dir
except ModuleNotFoundError:  # pragma: no cover - exercised by package imports
    from ..transfer import normalize_target, remote_manifest, validate_remote_dir


class SSHConnector(BaseHPCConnector):
    """Connector for SSH-based remote execution."""

    def __init__(self, host: str, user: str | None = None, port: int | None = None):
        self.host = host
        self.user = user
        self.port = port

    @property
    def target(self) -> dict:
        target = {"host": self.host}
        if self.user is not None:
            target["user"] = self.user
        if self.port is not None:
            target["port"] = self.port
        return normalize_target(target)

    def _remote_target(self) -> str:
        host = f"[{self.host}]" if ":" in self.host else self.host
        return "{}@{}".format(self.user, host) if self.user else host

    @staticmethod
    def _safe_error(value: object, fallback: str) -> str:
        """Return bounded SSH diagnostics without credential-path details."""
        text = str(value or "").strip()
        if not text:
            return fallback
        text = re.sub(
            r"(?i)(?:[A-Za-z]:)?[^\s\"']*[/\\]\.ssh[/\\][^\s\"']+",
            "<ssh-credential-path>",
            text,
        )
        text = re.sub(r"(?i)IdentityFile\s+\S+", "IdentityFile <redacted>", text)
        return text[:1000]

    def _ssh_cmd(self, remote_cmd: str) -> list:
        """Build SSH command."""
        cmd = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10"]
        if self.port is not None:
            cmd.extend(["-p", str(self.port)])
        cmd.extend([self._remote_target(), remote_cmd])
        return cmd

    def _scp_cmd(self, src: str, dst: str) -> list:
        """Build SCP command."""
        cmd = ["scp", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10"]
        if self.port is not None:
            cmd.extend(["-P", str(self.port)])
        cmd.extend([src, dst])
        return cmd

    @staticmethod
    def _validate_job_id(job_id: str) -> str:
        value = str(job_id)
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", value):
            raise ValueError("job_id contains forbidden characters")
        return value

    def _ensure_remote_dirs(self, remote_dir: str, files: list[str]) -> dict:
        remote_dir = validate_remote_dir(remote_dir)
        directories = {remote_dir}
        for fname in files:
            parent = posixpath.dirname(posixpath.join(remote_dir, fname))
            directories.add(parent or remote_dir)
        command = "mkdir -p -- " + " ".join(shlex.quote(item) for item in sorted(directories))
        proc = subprocess.run(self._ssh_cmd(command), capture_output=True, text=True, timeout=30)
        if proc.returncode != 0:
            return {"status": "error", "message": self._safe_error(proc.stderr, "remote directory creation failed")}
        return {"status": "success"}

    def list_remote_files(self, remote_dir: str, paths: list[str]) -> dict:
        """Expand remote files/directories without exposing arbitrary shell input."""
        remote_dir = validate_remote_dir(remote_dir)
        lines = []
        for fname in paths:
            safe = shlex.quote(fname)
            full = shlex.quote(posixpath.join(remote_dir, fname))
            lines.append(
                "if [ -f {full} ]; then printf '%s\\t%s\\n' FILE {fname}; "
                "elif [ -d {full} ]; then find {full} -type f -printf '%P\\n' | "
                "while IFS= read -r child; do printf '%s\\t%s/%s\\n' FILE {fname} \"$child\"; done; "
                "else printf '%s\\t%s\\n' MISSING {fname}; fi".format(full=full, fname=safe)
            )
        proc = subprocess.run(
            self._ssh_cmd("; ".join(lines)),
            capture_output=True,
            text=True,
            timeout=60,
        )
        if proc.returncode != 0:
            return {"status": "error", "message": self._safe_error(proc.stderr, "remote listing failed")}
        files = []
        missing = []
        for line in proc.stdout.splitlines():
            kind, _, value = line.partition("\t")
            if kind == "FILE" and value:
                files.append(value)
            elif kind == "MISSING" and value:
                missing.append(value)
        if missing:
            return {"status": "error", "message": "Remote paths not found", "missing": missing}
        return {"status": "success", "files": sorted(set(files))}

    def remote_file_manifest(self, remote_dir: str, files: list[str]) -> dict:
        remote_dir = validate_remote_dir(remote_dir)
        commands = []
        for fname in files:
            rel = shlex.quote(fname)
            full = shlex.quote(posixpath.join(remote_dir, fname))
            commands.append(
                "size=$(stat -c '%s' {full}); sha=$(sha256sum -- {full} | awk '{{print $1}}'); "
                "printf '%s\\t%s\\t%s\\n' {rel} \"$size\" \"$sha\"".format(rel=rel, full=full)
            )
        proc = subprocess.run(
            self._ssh_cmd("; ".join(commands)),
            capture_output=True,
            text=True,
            timeout=120,
        )
        if proc.returncode != 0:
            return {"status": "error", "message": self._safe_error(proc.stderr, "remote hash verification failed")}
        entries = []
        for line in proc.stdout.splitlines():
            parts = line.split("\t")
            if len(parts) != 3 or len(parts[2]) != 64:
                return {"status": "error", "message": "Malformed remote manifest output"}
            entries.append({"path": parts[0], "size_bytes": int(parts[1]), "sha256": parts[2]})
        return {"status": "success", "manifest": remote_manifest(entries)}

    def _remote_has_slurm(self) -> bool:
        """Check if the remote host has SLURM (sbatch) available."""
        try:
            cmd = self._ssh_cmd("which sbatch >/dev/null 2>&1 && echo yes || echo no")
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            return "yes" in proc.stdout
        except Exception:
            return False

    def dry_run(self, script_path: str, manifest_path: str = "", base_dir: str = ".") -> dict:
        """Validate a script exists locally.

        Accepts the same signature as SlurmConnector.dry_run for connector
        polymorphism. manifest_path and base_dir are accepted for signature
        compatibility but SSH dry-run only validates the local script.
        """
        issues = []
        if not self.host:
            issues.append("No SSH target host provided")

        try:
            if not os.path.exists(script_path):
                issues.append("Script not found locally: {}".format(script_path))
        except Exception:
            pass

        response = {
            "valid": len(issues) == 0,
            "issues": issues,
            "scheduler": "ssh",
            "target": self.target,
            "script": script_path,
        }
        if Path(script_path).exists():
            response["script_hash"] = self._sha256_file(script_path)
        return response

    def submit(
        self,
        script_path: str,
        *,
        project_root: str | None = None,
        approval_token: str | None = None,
        gate_decision_id: str | None = None,
        dry_run_evidence: str | None = None,
        script_hash: str | None = None,
        input_artifact_hash: str | None = None,
        transfer_manifest: str | None = None,
        remote_workdir: str | None = None,
        target: dict | None = None,
        approved: bool | None = None,
    ) -> dict:
        """Submit a job via SSH.

        Detects whether the remote host has SLURM:
        - If SLURM: copies script and uses sbatch
        - If no SLURM: copies script and uses nohup bash
        """
        auth = self.validate_submit_authorization(
            script_path,
            project_root=project_root,
            approval_token=approval_token,
            gate_decision_id=gate_decision_id,
            dry_run_evidence=dry_run_evidence,
            script_hash=script_hash,
            input_artifact_hash=input_artifact_hash,
            approval_bindings={"target": target, "remote_workdir": remote_workdir},
            approved=approved,
        )
        if auth["status"] != "success":
            return auth

        if not transfer_manifest:
            return {
                "status": "error",
                "message": "SSH submit requires a verified transfer_manifest",
                "code": "transfer_manifest_required",
            }
        manifest_path = self._resolve_evidence_path(Path(project_root), transfer_manifest)
        if manifest_path is None:
            return {"status": "error", "message": "Transfer manifest was not found", "code": "transfer_manifest_missing"}
        try:
            transfer = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            return {"status": "error", "message": f"Transfer manifest is invalid: {exc}", "code": "transfer_manifest_invalid"}
        if transfer.get("status") != "verified":
            return {"status": "error", "message": "Transfer manifest is not verified", "code": "transfer_manifest_unverified"}
        if transfer.get("direction") != "upload":
            return {"status": "error", "message": "SSH submit requires an upload transfer manifest", "code": "transfer_manifest_direction"}
        if transfer.get("target") != self.target:
            return {"status": "error", "message": "SSH target does not match transfer manifest", "code": "transfer_manifest_target_mismatch"}
        workdir = remote_workdir or transfer.get("remote_dir")
        if not workdir:
            return {"status": "error", "message": "remote_workdir is required for SSH submit", "code": "remote_workdir_required"}
        try:
            workdir = validate_remote_dir(workdir)
        except ValueError as exc:
            return {"status": "error", "message": str(exc), "code": "remote_workdir_invalid"}
        if transfer.get("remote_dir") != workdir:
            return {"status": "error", "message": "remote_workdir does not match transfer manifest", "code": "transfer_manifest_mismatch"}

        result = self.dry_run(script_path)
        if not result["valid"]:
            return {"success": False, "errors": result["issues"]}

        remote_path = posixpath.join(workdir, os.path.basename(script_path))
        source_manifest = transfer.get("source_manifest", {}).get("files", [])
        local_dir = Path(project_root) / transfer.get("local_dir", "")
        try:
            script_rel = Path(script_path).resolve().relative_to(local_dir.resolve()).as_posix()
        except ValueError:
            script_rel = Path(script_path).name
        if not any(item.get("path") == script_rel for item in source_manifest):
            return {
                "status": "error",
                "message": "Transferred source manifest does not include the submitted script",
                "code": "script_missing_from_transfer",
            }
        try:
            if self._remote_has_slurm():
                # Submit via sbatch
                exec_cmd = self._ssh_cmd("sbatch -- " + shlex.quote(remote_path))
                proc = subprocess.run(exec_cmd, capture_output=True, text=True, timeout=30)
                if proc.returncode == 0:
                    # Parse "Submitted batch job 12345"
                    from runtime.simflow_core.hpc import parse_slurm_job_id
                    job_id = parse_slurm_job_id(proc.stdout.strip())
                    if job_id:
                        return {
                            "success": True,
                            "status": "success",
                            "job_id": job_id,
                            "scheduler": "slurm",
                            "target": self.target,
                            "gate_decision_id": auth["gate_decision_id"],
                            "script_hash": auth["script_hash"],
                        }
                    return {
                        "success": True,
                        "status": "success",
                        "job_id": proc.stdout.strip(),
                        "scheduler": "slurm",
                        "target": self.target,
                        "gate_decision_id": auth["gate_decision_id"],
                        "script_hash": auth["script_hash"],
                    }
                return {"success": False, "errors": [self._safe_error(proc.stderr, "remote sbatch failed")]}
            else:
                # Fallback to nohup bash
                exec_cmd = self._ssh_cmd("nohup bash " + shlex.quote(remote_path) + " & echo $!")
                proc = subprocess.run(exec_cmd, capture_output=True, text=True, timeout=30)
                if proc.returncode == 0:
                    pid = proc.stdout.strip().split("\n")[-1]
                    return {
                        "success": True,
                        "status": "success",
                        "job_id": pid,
                        "scheduler": "ssh",
                        "target": self.target,
                        "gate_decision_id": auth["gate_decision_id"],
                        "script_hash": auth["script_hash"],
                    }
                return {"success": False, "errors": [self._safe_error(proc.stderr, "remote launch failed")]}

        except subprocess.TimeoutExpired:
            return {"success": False, "errors": ["SSH operation timed out"]}
        except Exception as e:
            return {"success": False, "errors": [self._safe_error(e, "SSH operation failed")]}

    def status(self, job_id: str) -> dict:
        """Check remote job status.

        For SLURM jobs: uses squeue then sacct.
        For nohup jobs: checks if PID is alive.
        """
        try:
            job_id = self._validate_job_id(job_id)
        except ValueError as exc:
            return {"status": "error", "message": str(exc), "code": "invalid_job_id"}

        # Try SLURM status first
        try:
            cmd = self._ssh_cmd(
                "squeue -j {} -h -o '%T %M %N' 2>/dev/null".format(job_id)
            )
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            if proc.returncode == 0 and proc.stdout.strip():
                parts = proc.stdout.strip().split()
                return {
                    "status": "success",
                    "data": {
                        "job_id": job_id,
                        "state": parts[0] if len(parts) > 0 else "unknown",
                        "runtime": parts[1] if len(parts) > 1 else None,
                        "nodes": parts[2] if len(parts) > 2 else None,
                        "scheduler": "slurm",
                    },
                }

            # Fallback to sacct
            cmd = self._ssh_cmd(
                "sacct -j {} --format=State,Elapsed,ExitCode --noheader --parsable2 "
                "2>/dev/null | head -1".format(job_id)
            )
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            if proc.returncode == 0 and proc.stdout.strip():
                parts = proc.stdout.strip().split("|")
                if parts and parts[0]:
                    return {
                        "status": "success",
                        "data": {
                            "job_id": job_id,
                            "state": parts[0],
                            "elapsed": parts[1] if len(parts) > 1 else None,
                            "exit_code": parts[2] if len(parts) > 2 else None,
                            "scheduler": "slurm",
                        },
                    }
        except Exception:
            pass

        # Fallback: check PID
        try:
            cmd = self._ssh_cmd(
                "kill -0 {} 2>/dev/null && echo running || echo completed".format(job_id)
            )
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            status = "running" if "running" in proc.stdout else "completed"
            return {
                "status": "success",
                "data": {"job_id": job_id, "state": status, "scheduler": "ssh", "target": self.target},
            }
        except Exception:
            return {"status": "success", "data": {"job_id": job_id, "state": "unknown"}}

    def cancel(self, job_id: str) -> dict:
        """Cancel a remote job (SLURM scancel or kill)."""
        try:
            job_id = self._validate_job_id(job_id)
        except ValueError as exc:
            return {"success": False, "error": str(exc), "code": "invalid_job_id"}

        # Try scancel first
        try:
            cmd = self._ssh_cmd("scancel {} 2>/dev/null".format(job_id))
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            if proc.returncode == 0:
                return {"success": True, "job_id": job_id, "scheduler": "slurm"}
        except Exception:
            pass

        # Fallback to kill
        try:
            cmd = self._ssh_cmd("kill -9 {}".format(job_id))
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            return {"success": proc.returncode == 0, "job_id": job_id}
        except Exception as e:
            return {"success": False, "error": self._safe_error(e, "SSH cancel failed")}

    def upload_files(self, local_dir: str, remote_dir: str, files: list[str]) -> dict:
        """Upload files to remote host via SCP."""
        if not self.host:
            return {"status": "error", "message": "No SSH host configured"}

        remote_dir = validate_remote_dir(remote_dir)
        directory_result = self._ensure_remote_dirs(remote_dir, files)
        if directory_result["status"] != "success":
            return directory_result

        errors = []
        uploaded = []
        for fname in files:
            local_path = os.path.join(local_dir, fname)
            remote_path = "{}:{}".format(self._remote_target(), posixpath.join(remote_dir, fname))
            try:
                cmd = self._scp_cmd(local_path, remote_path)
                proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                if proc.returncode != 0:
                    errors.append(f"Failed to upload {fname}: {self._safe_error(proc.stderr, 'SCP upload failed')}")
                else:
                    uploaded.append(fname)
            except subprocess.TimeoutExpired:
                errors.append(f"Timeout uploading {fname}")
            except Exception as e:
                errors.append(f"Error uploading {fname}: {self._safe_error(e, 'SCP upload failed')}")

        if errors:
            return {"status": "error", "errors": errors, "uploaded_files": uploaded}
        return {"status": "success", "uploaded": len(uploaded), "files": uploaded}

    def download_files(self, remote_dir: str, local_dir: str, files: list[str]) -> dict:
        """Download files from remote host via SCP."""
        if not self.host:
            return {"status": "error", "message": "No SSH host configured"}

        remote_dir = validate_remote_dir(remote_dir)
        Path(local_dir).mkdir(parents=True, exist_ok=True)

        errors = []
        downloaded = []
        for fname in files:
            remote_path = "{}:{}".format(self._remote_target(), posixpath.join(remote_dir, fname))
            local_path = os.path.join(local_dir, fname)
            Path(local_path).parent.mkdir(parents=True, exist_ok=True)
            try:
                cmd = self._scp_cmd(remote_path, local_path)
                proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
                if proc.returncode != 0:
                    errors.append(f"Failed to download {fname}: {self._safe_error(proc.stderr, 'SCP download failed')}")
                else:
                    downloaded.append(fname)
            except subprocess.TimeoutExpired:
                errors.append(f"Timeout downloading {fname}")
            except Exception as e:
                errors.append(f"Error downloading {fname}: {self._safe_error(e, 'SCP download failed')}")

        if errors:
            return {"status": "error", "errors": errors, "downloaded_files": downloaded}
        return {"status": "success", "downloaded": len(downloaded), "files": downloaded}
