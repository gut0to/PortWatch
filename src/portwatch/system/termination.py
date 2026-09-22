import psutil

from portwatch.domain.exceptions import ProcessTerminationError


class ProcessTerminator:
    def terminate(self, pid: int, force: bool = False, wait_seconds: float = 0.5) -> None:
        try:
            process = psutil.Process(pid)
            process.terminate()
            try:
                process.wait(timeout=wait_seconds)
            except psutil.TimeoutExpired as error:
                if not force:
                    raise ProcessTerminationError(
                        "Process did not exit after a graceful termination request."
                    ) from error
                process.kill()
                process.wait(timeout=wait_seconds)
        except psutil.NoSuchProcess:
            # A process can exit between discovery and termination; that is already success.
            return
        except (psutil.AccessDenied, psutil.ZombieProcess, OSError) as error:
            raise ProcessTerminationError(f"Could not terminate process {pid}: {error}") from error
