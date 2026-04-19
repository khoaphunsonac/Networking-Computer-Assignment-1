"""Hybrid chat state and non-blocking peer networking helpers.

This module provides an event-driven peer node built on selectors so each
sample app instance can participate in direct P2P messaging while still using
REST APIs for peer discovery and channel management.
"""

from __future__ import annotations

import json
import selectors
import socket
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set


def _utc_now() -> str:
    """Return a UTC ISO timestamp string."""
    return datetime.now(timezone.utc).isoformat()


@dataclass
class _ConnState:
    """Runtime state associated with a single socket connection."""

    socket_obj: socket.socket
    peer_id: str = ""
    recv_buffer: bytearray = field(default_factory=bytearray)
    send_buffer: bytearray = field(default_factory=bytearray)
    connected: bool = False


class HybridChatNode:
    """Maintain tracker state and a non-blocking P2P chat daemon."""

    def __init__(self, peer_id: str, listen_ip: str, listen_port: int) -> None:
        self.peer_id = peer_id
        self.listen_ip = listen_ip
        self.listen_port = listen_port

        self._selector = selectors.DefaultSelector()
        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._server_socket: Optional[socket.socket] = None

        self.peers: Dict[str, Dict[str, object]] = {}
        self.channels: Dict[str, Set[str]] = defaultdict(set)
        self.channel_messages: Dict[str, List[Dict[str, object]]] = defaultdict(list)
        self.notifications: Dict[str, int] = defaultdict(int)

        self._connections: Dict[str, _ConnState] = {}
        self._socket_to_state: Dict[socket.socket, _ConnState] = {}

    def start(self) -> None:
        """Start the non-blocking P2P listener in a daemon thread."""
        with self._lock:
            if self._running:
                return

            server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind((self.listen_ip, self.listen_port))
            server.listen(50)
            server.setblocking(False)

            self._server_socket = server
            self._selector.register(server, selectors.EVENT_READ, data="accept")
            self._running = True

            self._thread = threading.Thread(target=self._event_loop, daemon=True)
            self._thread.start()

    def stop(self) -> None:
        """Stop all sockets and terminate the event loop."""
        with self._lock:
            self._running = False

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)

        for state in list(self._socket_to_state.values()):
            self._close_connection(state)

        if self._server_socket is not None:
            try:
                self._selector.unregister(self._server_socket)
            except Exception:
                pass
            try:
                self._server_socket.close()
            except Exception:
                pass
            self._server_socket = None

    def register_peer(self, peer_id: str, ip: str, port: int) -> Dict[str, object]:
        """Register or refresh a peer in the tracker list."""
        with self._lock:
            self.peers[peer_id] = {
                "peer_id": peer_id,
                "ip": ip,
                "port": int(port),
                "updated_at": _utc_now(),
            }
            return dict(self.peers[peer_id])

    def add_peer_list(self, peers: List[Dict[str, object]]) -> int:
        """Merge a list of peers received from another node/server."""
        added = 0
        for peer in peers:
            peer_id = str(peer.get("peer_id", "")).strip()
            ip = str(peer.get("ip", "")).strip()
            port = int(peer.get("port", 0) or 0)
            if not peer_id or not ip or port <= 0:
                continue
            self.register_peer(peer_id, ip, port)
            added += 1
        return added

    def get_peer_list(self) -> List[Dict[str, object]]:
        """Return a snapshot of known peers."""
        with self._lock:
            return [dict(item) for item in self.peers.values()]

    def join_channel(self, channel: str) -> None:
        """Join a local channel membership set for UI listing."""
        name = channel.strip() or "general"
        with self._lock:
            self.channels[name].add(self.peer_id)

    def list_channels(self) -> List[Dict[str, object]]:
        """Return channels and unread counters for this peer."""
        with self._lock:
            return [
                {
                    "channel": channel,
                    "members": sorted(list(members)),
                    "unread": int(self.notifications.get(channel, 0)),
                    "messages": len(self.channel_messages.get(channel, [])),
                }
                for channel, members in self.channels.items()
            ]

    def get_channel_messages(self, channel: str, limit: int = 50) -> List[Dict[str, object]]:
        """Fetch the latest messages for a channel and clear unread count."""
        name = channel.strip() or "general"
        with self._lock:
            self.notifications[name] = 0
            return list(self.channel_messages.get(name, []))[-max(limit, 1):]

    def connect_peer(self, peer_id: str, ip: str, port: int) -> Dict[str, object]:
        """Create a non-blocking outgoing connection to another peer."""
        peer_id = peer_id.strip()
        if not peer_id:
            raise ValueError("peer_id is required")

        self.register_peer(peer_id, ip, port)

        with self._lock:
            if peer_id in self._connections:
                return {"peer_id": peer_id, "status": "already-connected"}

            conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            conn.setblocking(False)
            try:
                conn.connect_ex((ip, int(port)))
            except OSError as exc:
                conn.close()
                raise ConnectionError(str(exc)) from exc

            state = _ConnState(socket_obj=conn, peer_id=peer_id, connected=False)
            self._connections[peer_id] = state
            self._socket_to_state[conn] = state
            self._selector.register(conn, selectors.EVENT_READ | selectors.EVENT_WRITE, data="peer")

        return {"peer_id": peer_id, "status": "connecting"}

    def send_to_peer(
        self,
        peer_id: str,
        message: str,
        channel: str = "general",
        sender: Optional[str] = None,
    ) -> Dict[str, object]:
        """Queue a chat message for a specific connected peer."""
        sender = sender or self.peer_id
        payload = {
            "type": "chat",
            "channel": channel,
            "from": sender,
            "message": message,
            "timestamp": _utc_now(),
        }
        encoded = (json.dumps(payload) + "\n").encode("utf-8")

        with self._lock:
            state = self._connections.get(peer_id)
            if state is None:
                return {"peer_id": peer_id, "status": "not-connected"}
            state.send_buffer.extend(encoded)

        self._store_message(channel, sender, message, direction="outgoing")
        return {"peer_id": peer_id, "status": "queued"}

    def broadcast(
        self,
        message: str,
        channel: str = "general",
        sender: Optional[str] = None,
    ) -> Dict[str, object]:
        """Queue one message to all currently connected peers."""
        sender = sender or self.peer_id
        with self._lock:
            peers = list(self._connections.keys())

        delivered = 0
        for peer_id in peers:
            result = self.send_to_peer(peer_id, message, channel=channel, sender=sender)
            if result.get("status") == "queued":
                delivered += 1

        return {"delivered": delivered, "target_peers": len(peers)}

    def _event_loop(self) -> None:
        """Run selector-driven accept/read/write processing."""
        while self._running:
            events = self._selector.select(timeout=0.2)
            for key, mask in events:
                data = key.data
                if data == "accept":
                    self._handle_accept(key.fileobj)
                    continue

                state = self._socket_to_state.get(key.fileobj)
                if state is None:
                    continue

                if mask & selectors.EVENT_WRITE:
                    self._handle_write(state)
                if mask & selectors.EVENT_READ:
                    self._handle_read(state)

    def _handle_accept(self, server_socket: socket.socket) -> None:
        """Accept inbound non-blocking peer connections."""
        try:
            conn, _addr = server_socket.accept()
            conn.setblocking(False)
            state = _ConnState(socket_obj=conn, connected=True)
            with self._lock:
                self._socket_to_state[conn] = state
                self._selector.register(conn, selectors.EVENT_READ | selectors.EVENT_WRITE, data="peer")
        except BlockingIOError:
            return
        except OSError:
            return

    def _handle_write(self, state: _ConnState) -> None:
        """Flush pending outbound data without blocking the loop."""
        if not state.connected:
            error_code = state.socket_obj.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
            if error_code != 0:
                self._close_connection(state)
                return
            state.connected = True

        if not state.send_buffer:
            return

        try:
            sent = state.socket_obj.send(state.send_buffer)
            if sent > 0:
                del state.send_buffer[:sent]
        except BlockingIOError:
            return
        except OSError:
            self._close_connection(state)

    def _handle_read(self, state: _ConnState) -> None:
        """Read incoming bytes and decode newline-delimited JSON messages."""
        try:
            data = state.socket_obj.recv(4096)
            if not data:
                self._close_connection(state)
                return
            state.recv_buffer.extend(data)
        except BlockingIOError:
            return
        except OSError:
            self._close_connection(state)
            return

        while b"\n" in state.recv_buffer:
            raw_line, _, remain = state.recv_buffer.partition(b"\n")
            state.recv_buffer = bytearray(remain)
            if not raw_line:
                continue
            try:
                payload = json.loads(raw_line.decode("utf-8"))
            except json.JSONDecodeError:
                continue
            self._handle_payload(state, payload)

    def _handle_payload(self, state: _ConnState, payload: Dict[str, object]) -> None:
        """Apply side effects for one received chat payload."""
        sender = str(payload.get("from", "")).strip() or "unknown"
        message = str(payload.get("message", "")).strip()
        channel = str(payload.get("channel", "general")).strip() or "general"

        if not message:
            return

        if not state.peer_id and sender != "unknown":
            state.peer_id = sender
            with self._lock:
                self._connections[sender] = state

        self.register_peer(sender, payload.get("ip", "127.0.0.1") or "127.0.0.1", int(payload.get("port", 0) or 0))
        self.join_channel(channel)
        self._store_message(channel, sender, message, direction="incoming")

    def _store_message(self, channel: str, sender: str, message: str, direction: str) -> None:
        """Append one immutable message entry and update unread counters."""
        entry = {
            "from": sender,
            "message": message,
            "channel": channel,
            "timestamp": _utc_now(),
            "direction": direction,
        }
        with self._lock:
            self.channels[channel].add(self.peer_id)
            self.channel_messages[channel].append(entry)
            if direction == "incoming":
                self.notifications[channel] += 1

    def _close_connection(self, state: _ConnState) -> None:
        """Unregister and close a connection socket safely."""
        with self._lock:
            sock = state.socket_obj
            for peer_id, conn_state in list(self._connections.items()):
                if conn_state is state:
                    self._connections.pop(peer_id, None)
            self._socket_to_state.pop(sock, None)

            try:
                self._selector.unregister(sock)
            except Exception:
                pass
            try:
                sock.close()
            except Exception:
                pass


def wait_for_connection(node: HybridChatNode, peer_id: str, timeout_seconds: float = 3.0) -> bool:
    """Poll connection state for a short timeout window."""
    end = time.time() + max(timeout_seconds, 0.2)
    while time.time() < end:
        with node._lock:
            state = node._connections.get(peer_id)
            if state and state.connected:
                return True
        time.sleep(0.05)
    return False
