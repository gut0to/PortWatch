import os

import psutil

from portwatch.domain.exceptions import PermissionDeniedError, ProcessTerminationError


class ProcessTerminator:
    def terminate(self, pid: int, force: bool = False, wait_seconds: float = 0.5) -> None:
        if pid == os.getpid():
            raise ProcessTerminationError("PortWatch cannot terminate itself.")
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
        except psutil.TimeoutExpired as error:
            raise ProcessTerminationError(
                f"Process {pid} did not exit after forced termination."
            ) from error
        except psutil.AccessDenied as error:
            raise PermissionDeniedError(f"Permission denied terminating process {pid}.") from error
        except OSError as error:
            raise ProcessTerminationError(f"Could not terminate process {pid}: {error}") from error
