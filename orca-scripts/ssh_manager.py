import logging
import paramiko
import sys
import threading

from multiprocessing import Queue


class SSHWorker(threading.Thread):
    def __init__(self, hostname: str, cmd_queue: Queue, result_queue: Queue):
        super().__init__()
        self.hostname: str = hostname
        self.cmd_queue: Queue = cmd_queue
        self.result_queue: Queue = result_queue
        self.ssh_client: paramiko.SSHClient | None = None

    def run(self) -> None:
        self.ssh_client = paramiko.SSHClient()
        self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            self.ssh_client.connect(self.hostname)
            while True:
                cmd: str = self.cmd_queue.get()
                if cmd is None:
                    break
                stdin, stdout, stderr = self.ssh_client.exec_command(cmd)
                output: str = stdout.read().decode().strip()
                self.result_queue.put((self.hostname, output))
        except Exception as e:
            self.result_queue.put((self.hostname, f"Connection failed: {e}"))
        finally:
            if self.ssh_client:
                self.ssh_client.close()


class SSHManager:
    def __init__(self, hostnames: list[str]):
        logging.info(f"Connecting to {len(hostnames)} hosts")

        self.hostnames: list[str] = hostnames
        self.result_queue: Queue = Queue()
        self.workers: list[SSHWorker] = []
        self.worker_map: dict[str, SSHWorker] = {}
        self.worker_cmd_queues: dict[str, Queue] = {}
        self._unreachable_hosts: list[str] = []
        self._setup_workers()

    def _setup_workers(self) -> None:
        for hostname in self.hostnames:
            try:
                worker_queue = Queue()
                worker = SSHWorker(hostname, worker_queue, self.result_queue)
                worker.start()
                self.workers.append(worker)
                self.worker_map[hostname] = worker
                self.worker_cmd_queues[hostname] = worker_queue
            except Exception as e:
                logging.error(f"Failed to connect to {hostname}: {e}")
                self._unreachable_hosts.append(hostname)

        logging.info(f"Connected to {len(self.workers)} hosts")

    def get_unreachable_hosts(self) -> list[str]:
        return [h for h in self._unreachable_hosts]

    def run_cmd(self, cmd: str) -> list[tuple[str, str]]:
        logging.info(f"Running command: {cmd}")

        for worker_queue in self.worker_cmd_queues.values():
            worker_queue.put(cmd)

        responses: list[tuple[str, str]] = []
        for _ in self.hostnames:
            responses.append(self.result_queue.get())

        sort_by_hostname = lambda x: int(x[0].split(".")[0].replace("h", ""))
        responses = sorted(responses, key=sort_by_hostname)

        return responses

    def run_cmd_on_hosts(self, hostnames: list[str], cmd: str) -> list[tuple[str, str]]:
        logging.info(f"Running command: {cmd} on hosts: {hostnames}")

        for hostname in hostnames:
            host_queue = self.worker_cmd_queues.get(hostname)
            assert host_queue is not None, f"Host {hostname} is unreachable"
            host_queue.put(cmd)

        responses: list[tuple[str, str]] = []
        for _ in hostnames:
            responses.append(self.result_queue.get())

        sort_by_hostname = lambda x: int(x[0].split(".")[0].replace("h", ""))
        responses = sorted(responses, key=sort_by_hostname)

        return responses

    def stop_workers(self) -> None:
        for q in self.worker_cmd_queues.values():
            q.put(None)
        for worker in self.workers:
            worker.join()

    def __del__(self):
        self.stop_workers()


def run():
    hosts = [f"h{i}" for i in range(4)]
    sshm = SSHManager(hosts)
    print(sshm.run_cmd("ls"))
    pass


if __name__ == "__main__":
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    run()
