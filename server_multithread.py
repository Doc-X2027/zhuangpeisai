"""TCP command server used by the competition GUI."""
from __future__ import annotations
import socket
import threading
from typing import Callable

class CompetitionTCPServer:
    def __init__(self, host: str = "0.0.0.0", port: int = 8888, command_handler: Callable | None = None,
                 feedback_handler: Callable | None = None, read_handler: Callable | None = None) -> None:
        self.host, self.port, self.command_handler = host, port, command_handler
        self.feedback_handler = feedback_handler
        self.read_handler = read_handler
        self._socket = None
        self._stop = threading.Event()

    def serve_forever(self) -> None:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind((self.host, self.port)); server.listen(); server.settimeout(0.5)
            self._socket = server
            while not self._stop.is_set():
                try: client, addr = server.accept()
                except socket.timeout: continue
                except OSError: break
                threading.Thread(target=self.handle_client,args=(client,addr),daemon=True).start()

    def shutdown(self) -> None:
        self._stop.set()
        if self._socket:
            try: self._socket.close()
            except OSError: pass

    def handle_client(self, client: socket.socket, addr: tuple[str,int]) -> None:
        try:
            first_data=client.recv(4096)
            lowered=first_data.lower()
            command=next((name for name in ("identify","planning","auto") if lowered.startswith(name.encode("ascii"))),"")
            initial_feedback=first_data[len(command):] if command else b""
            if lowered.strip(b"\x00\r\n\t ")==b"read" and self.read_handler:
                response=self.read_handler(addr)
            elif command not in ("identify","planning","auto"):
                text=first_data.decode("utf-8",errors="replace")
                if self.feedback_handler and text:
                    self.feedback_handler(text,addr)
                    response="OK"
                else:
                    response="Process failure: unsupported command"
            elif self.command_handler:
                outcome={}; completed=threading.Event()
                def run_command():
                    try: outcome["response"]=self.command_handler(command,addr)
                    except Exception as exc: outcome["error"]=exc
                    finally: completed.set()
                threading.Thread(target=run_command,daemon=True).start()
                if initial_feedback and self.feedback_handler:
                    self.feedback_handler(initial_feedback.decode("utf-8",errors="replace"),addr)
                client.settimeout(0.1)
                peer_open=True
                while not completed.wait(0.05):
                    try: data=client.recv(4096)
                    except socket.timeout: continue
                    if not data:
                        peer_open=False; break
                    text=data.decode("utf-8",errors="replace")
                    if self.feedback_handler and text:
                        self.feedback_handler(text,addr)
                completed.wait()
                if "error" in outcome: raise outcome["error"]
                response=outcome.get("response","Process failure")
                if not peer_open: return
            else:
                response="Process failure: GUI command handler unavailable"
            client.sendall(str(response).encode("utf-8"))
        except Exception as exc:
            try: client.sendall(f"Process failure: {exc}".encode("utf-8"))
            except OSError: pass
        finally: client.close()

def main() -> None:
    CompetitionTCPServer().serve_forever()
if __name__ == "__main__": main()
