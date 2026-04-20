#
# Copyright (C) 2026 pdnguyen of HCMC University of Technology VNU-HCM.
# All rights reserved.
# This file is part of the CO3093/CO3094 course,
# and is released under the "MIT License Agreement". Please see the LICENSE
# file that should have been included as part of this package.
#
# AsynapRous release
#
# The authors hereby grant to Licensee personal permission to use
# and modify the Licensed Source Code for the sole purpose of studying
# while attending the course
#


"""Sample REST app routes plus hybrid chat APIs."""

import json
import threading
from urllib.parse import parse_qs, unquote_plus

from daemon import AsynapRous
from .hybrid_chat import HybridChatNode, wait_for_connection

app = AsynapRous()
_state_lock = threading.Lock()
chat_state = {
    "node": None,
    "peer_id": "peer-default",
}


def _read_json(body):
    """Decode JSON body into dict, fallback to empty dict."""
    if not body:
        return {}
    if isinstance(body, bytes):
        body = body.decode("utf-8", errors="replace")
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return {}


def _json_response(payload):
    return json.dumps(payload).encode("utf-8")


def _get_node():
    with _state_lock:
        return chat_state.get("node")


@app.route('/login', methods=['POST'])
def login(req, resp):
    """Authenticate one user and return a lightweight session token."""
    payload = _read_json(req.body)
    raw_body = ""
    if not payload and req.body:
        raw_body = req.body
        if isinstance(raw_body, bytes):
            raw_body = raw_body.decode("utf-8", errors="replace")
        else:
            raw_body = str(raw_body)

        form_data = parse_qs(raw_body, keep_blank_values=True)
        payload = {key: values[0] if values else "" for key, values in form_data.items()}

    # Fallback for unusual form body shapes that bypass parse_qs.
    if not payload.get("username") and raw_body and "username=" in raw_body:
        candidate = raw_body.split("username=", 1)[1].split("&", 1)[0]
        payload["username"] = unquote_plus(candidate)

    username = str(payload.get("username") or payload.get("user") or "guest").strip() or "guest"

    with _state_lock:
        chat_state["peer_id"] = username

    data = {
        "message": "Welcome to the RESTful TCP WebApp",
        "peer_id": username,
        "session": "token-{}".format(username),
    }
    resp.headers["Set-Cookie"] = "session_id={}; Path=/; HttpOnly".format(data["session"])
    resp.headers["Content-Type"] = "application/json; charset=utf-8"
    return _json_response(data)

@app.route("/echo", methods=["POST"])
def echo(headers="guest", body="anonymous"):
    print("[SampleApp] received body {}".format(body))

    try:
        message = json.loads(body)
        data = {"received": message }
        # Convert to JSON string
        json_str = json.dumps(data)
        return (json_str.encode("utf-8"))
    except json.JSONDecodeError:
        data = {"error": "Invalid JSON"}
        # Convert to JSON string
        json_str = json.dumps(data)
        return (json_str.encode("utf-8"))


@app.route('/submit-info', methods=['POST'])
def submit_info(headers="guest", body=""):
    """Register peer address in centralized tracker list."""
    payload = _read_json(body)
    node = _get_node()
    if node is None:
        return _json_response({"error": "chat node is not initialized"})

    peer_id = str(payload.get("peer_id") or payload.get("username") or "").strip()
    ip = str(payload.get("ip") or payload.get("host") or "").strip()
    port = int(payload.get("port") or 0)
    if not peer_id or not ip or port <= 0:
        return _json_response({"error": "peer_id, ip, and port are required"})

    peer = node.register_peer(peer_id, ip, port)
    return _json_response({"status": "ok", "peer": peer})


@app.route('/add-list', methods=['POST'])
def add_list(headers="guest", body=""):
    """Merge one peer list snapshot from client/server sync."""
    payload = _read_json(body)
    peers = payload.get("peers", []) if isinstance(payload, dict) else []
    node = _get_node()
    if node is None:
        return _json_response({"error": "chat node is not initialized"})

    if not isinstance(peers, list):
        return _json_response({"error": "peers must be a list"})

    added = node.add_peer_list(peers)
    return _json_response({"status": "ok", "added": added})


@app.route('/get-list', methods=['GET', 'POST'])
def get_list(headers="guest", body=""):
    """Return current peer tracking list for discovery phase."""
    node = _get_node()
    if node is None:
        return _json_response({"error": "chat node is not initialized"})
    return _json_response({"status": "ok", "peers": node.get_peer_list()})


@app.route('/connect-peer', methods=['POST'])
def connect_peer(headers="guest", body=""):
    """Start non-blocking outgoing connection to one peer."""
    payload = _read_json(body)
    node = _get_node()
    if node is None:
        return _json_response({"error": "chat node is not initialized"})

    peer_id = str(payload.get("peer_id") or "").strip()
    ip = str(payload.get("ip") or payload.get("host") or "").strip()
    port = int(payload.get("port") or 0)
    if not peer_id or not ip or port <= 0:
        return _json_response({"error": "peer_id, ip, and port are required"})

    try:
        status = node.connect_peer(peer_id, ip, port)
    except Exception as exc:
        return _json_response({"error": "connect failed", "details": str(exc)})

    connected = wait_for_connection(node, peer_id, timeout_seconds=1.5)
    status["connected"] = connected
    return _json_response({"status": "ok", "result": status})


@app.route('/broadcast-peer', methods=['POST'])
def broadcast_peer(headers="guest", body=""):
    """Broadcast one message to all connected peers."""
    payload = _read_json(body)
    node = _get_node()
    if node is None:
        return _json_response({"error": "chat node is not initialized"})

    text = str(payload.get("message") or "").strip()
    channel = str(payload.get("channel") or "general").strip() or "general"
    sender = str(payload.get("from") or chat_state.get("peer_id") or "unknown").strip()
    if not text:
        return _json_response({"error": "message is required"})

    node.join_channel(channel)
    result = node.broadcast(text, channel=channel, sender=sender)
    return _json_response({"status": "ok", "result": result})


@app.route('/send-peer', methods=['POST'])
def send_peer(headers="guest", body=""):
    """Send one message directly to one selected peer."""
    payload = _read_json(body)
    node = _get_node()
    if node is None:
        return _json_response({"error": "chat node is not initialized"})

    peer_id = str(payload.get("peer_id") or "").strip()
    text = str(payload.get("message") or "").strip()
    channel = str(payload.get("channel") or "general").strip() or "general"
    sender = str(payload.get("from") or chat_state.get("peer_id") or "unknown").strip()
    if not peer_id or not text:
        return _json_response({"error": "peer_id and message are required"})

    node.join_channel(channel)
    result = node.send_to_peer(peer_id, text, channel=channel, sender=sender)
    return _json_response({"status": "ok", "result": result})


@app.route('/join-channel', methods=['POST'])
def join_channel(headers="guest", body=""):
    """Join or create a local channel for the current peer."""
    payload = _read_json(body)
    node = _get_node()
    if node is None:
        return _json_response({"error": "chat node is not initialized"})

    channel = str(payload.get("channel") or "general").strip() or "general"
    node.join_channel(channel)
    return _json_response({"status": "ok", "channel": channel})


@app.route('/channel-list', methods=['GET', 'POST'])
def channel_list(headers="guest", body=""):
    """List channels and unread counters for UI rendering."""
    node = _get_node()
    if node is None:
        return _json_response({"error": "chat node is not initialized"})

    channels = node.list_channels()
    return _json_response({"status": "ok", "channels": channels})


@app.route('/channel-messages', methods=['POST'])
def channel_messages(headers="guest", body=""):
    """Fetch scrollable immutable messages in one channel."""
    payload = _read_json(body)
    node = _get_node()
    if node is None:
        return _json_response({"error": "chat node is not initialized"})

    channel = str(payload.get("channel") or "general").strip() or "general"
    limit = int(payload.get("limit") or 50)
    messages = node.get_channel_messages(channel, limit=limit)
    return _json_response({"status": "ok", "channel": channel, "messages": messages})


@app.route('/hello', methods=['PUT'])
async def hello(headers, body):
    """
    Handle greeting via PUT request.

    This route prints a greeting message to the console using the provided headers
    and body.

    :param headers (str): The request headers or user identifier.
    :param body (str): The request body or message payload.
    """
    print("[SampleApp] ['PUT'] **ASYNC** Hello in {} to {}".format(headers, body))
    data =  {"id": 1, "name": "Alice", "email": "alice@example.com"}

    # Convert to JSON string
    json_str = json.dumps(data)
    return (json_str.encode("utf-8"))

def create_sampleapp(ip, port):
    """Create HTTP app and boot an internal P2P non-blocking daemon."""
    p2p_port = int(port) + 1000
    peer_id = "peer-{}".format(port)
    node = HybridChatNode(peer_id=peer_id, listen_ip=ip, listen_port=p2p_port)
    node.start()
    node.join_channel("general")

    with _state_lock:
        chat_state["node"] = node
        chat_state["peer_id"] = peer_id

    app.prepare_address(ip, port)
    app.run()

