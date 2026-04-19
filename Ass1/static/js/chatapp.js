(function () {
    "use strict";

    var state = {
        username: "",
        channel: "general",
        peers: [],
        pollTimer: null,
        connected: false,
    };

    var loginPanel = document.getElementById("loginPanel");
    var chatPanel = document.getElementById("chatPanel");
    var loginForm = document.getElementById("loginForm");
    var connectForm = document.getElementById("connectForm");
    var messageForm = document.getElementById("messageForm");
    var logoutBtn = document.getElementById("logoutBtn");

    var peerList = document.getElementById("peerList");
    var targetPeerSelect = document.getElementById("targetPeerSelect");
    var sendTypeSelect = document.getElementById("sendTypeSelect");
    var messagesBox = document.getElementById("messagesBox");
    var activeChannelTitle = document.getElementById("activeChannelTitle");
    var sessionInfo = document.getElementById("sessionInfo");

    function notify(message) {
        var toast = document.getElementById("toast");
        toast.textContent = message;
        toast.classList.add("show");
        setTimeout(function () {
            toast.classList.remove("show");
        }, 2200);
    }

    async function api(path, method, payload) {
        var opts = {
            method: method,
            headers: {
                "Content-Type": "application/json"
            }
        };

        if (payload) {
            opts.body = JSON.stringify(payload);
        }

        var response = await fetch(path, opts);
        var text = await response.text();
        var data = {};
        try {
            data = JSON.parse(text);
        } catch (_err) {
            data = { raw: text };
        }

        if (!response.ok || data.error) {
            throw new Error(data.error || ("HTTP " + response.status));
        }

        return data;
    }

    function renderPeers() {
        peerList.innerHTML = "";
        targetPeerSelect.innerHTML = "";

        var placeholder = document.createElement("option");
        placeholder.value = "";
        placeholder.textContent = "Select peer...";
        targetPeerSelect.appendChild(placeholder);

        state.peers.forEach(function (peer) {
            var item = document.createElement("li");
            item.textContent = peer.peer_id + " (" + peer.ip + ":" + peer.port + ")";
            peerList.appendChild(item);

            var option = document.createElement("option");
            option.value = peer.peer_id;
            option.textContent = peer.peer_id;
            targetPeerSelect.appendChild(option);
        });
    }

    function renderMessages(messages) {
        messagesBox.innerHTML = "";

        if (!messages.length) {
            var empty = document.createElement("div");
            empty.className = "msg-item";
            empty.textContent = "Welcome to the general chat room!";
            messagesBox.appendChild(empty);
            return;
        }

        messages.forEach(function (msg) {
            var wrapper = document.createElement("div");
            wrapper.className = "msg-item" + (msg.direction === "outgoing" ? " outgoing" : "");

            var meta = document.createElement("div");
            meta.className = "msg-meta";
            meta.textContent = msg.from + " • " + new Date(msg.timestamp).toLocaleTimeString();

            var content = document.createElement("div");
            content.textContent = msg.message;

            wrapper.appendChild(meta);
            wrapper.appendChild(content);
            messagesBox.appendChild(wrapper);
        });

        messagesBox.scrollTop = messagesBox.scrollHeight;
    }

    async function refreshPeerList() {
        var listResult = await api("/get-list", "GET");
        state.peers = (listResult.peers || []).filter(function (peer) {
            return peer.peer_id !== ("peer-" + window.location.port);
        });
        renderPeers();
    }

    async function refreshMessages() {
        var result = await api("/channel-messages", "POST", {
            channel: state.channel,
            limit: 100,
        });
        renderMessages(result.messages || []);
    }

    async function initialSync() {
        await api("/join-channel", "POST", { channel: state.channel });
        await refreshPeerList();
        await refreshMessages();
    }

    function startPolling() {
        if (state.pollTimer) {
            clearInterval(state.pollTimer);
        }
        state.pollTimer = setInterval(function () {
            refreshPeerList().catch(function () {
                notify("Không cập nhật được danh sách peer.");
            });
            refreshMessages().catch(function () {
                notify("Không cập nhật được tin nhắn.");
            });
        }, 2000);
    }

    function stopPolling() {
        if (state.pollTimer) {
            clearInterval(state.pollTimer);
            state.pollTimer = null;
        }
    }

    loginForm.addEventListener("submit", async function (event) {
        event.preventDefault();
        var username = document.getElementById("usernameInput").value.trim();
        var selfIp = document.getElementById("selfIpInput").value.trim();
        var selfP2pPort = parseInt(document.getElementById("selfP2pPortInput").value, 10);

        try {
            var loginResult = await api("/login", "POST", { username: username });
            state.username = username;

            await api("/submit-info", "POST", {
                peer_id: "peer-" + window.location.port,
                ip: selfIp,
                port: selfP2pPort,
            });

            activeChannelTitle.textContent = "General Chat";
            sessionInfo.textContent = "Logged as " + loginResult.peer_id + " • HTTP " + window.location.port;

            loginPanel.classList.add("hidden");
            chatPanel.classList.remove("hidden");

            state.connected = true;
            await initialSync();
            startPolling();
            notify("Đăng nhập thành công.");
        } catch (err) {
            notify("Login lỗi: " + err.message);
        }
    });

    connectForm.addEventListener("submit", async function (event) {
        event.preventDefault();
        try {
            var peerId = document.getElementById("peerIdInput").value.trim();
            var ip = document.getElementById("peerIpInput").value.trim();
            var port = parseInt(document.getElementById("peerPortInput").value, 10);

            var result = await api("/connect-peer", "POST", {
                peer_id: peerId,
                ip: ip,
                port: port,
            });

            await refreshPeerList();
            notify("Connect status: " + (result.result.status || "ok"));
        } catch (err) {
            notify("Connect lỗi: " + err.message);
        }
    });

    sendTypeSelect.addEventListener("change", function () {
        var isDirect = sendTypeSelect.value === "direct";
        targetPeerSelect.disabled = !isDirect;
    });
    targetPeerSelect.disabled = true;

    messageForm.addEventListener("submit", async function (event) {
        event.preventDefault();

        var text = document.getElementById("messageInput").value.trim();
        if (!text) {
            return;
        }

        try {
            if (sendTypeSelect.value === "direct") {
                var targetPeer = targetPeerSelect.value;
                if (!targetPeer) {
                    notify("Chọn peer nhận khi gửi direct.");
                    return;
                }

                await api("/send-peer", "POST", {
                    peer_id: targetPeer,
                    from: state.username,
                    channel: state.channel,
                    message: text,
                });
            } else {
                await api("/broadcast-peer", "POST", {
                    from: state.username,
                    channel: state.channel,
                    message: text,
                });
            }

            document.getElementById("messageInput").value = "";
            await refreshMessages();
        } catch (err) {
            notify("Gửi tin nhắn lỗi: " + err.message);
        }
    });

    logoutBtn.addEventListener("click", function () {
        stopPolling();
        state.connected = false;
        state.username = "";
        state.peers = [];

        chatPanel.classList.add("hidden");
        loginPanel.classList.remove("hidden");
        renderPeers();
        renderMessages([]);

        notify("Đã logout.");
    });

    window.addEventListener("beforeunload", function () {
        stopPolling();
    });
})();