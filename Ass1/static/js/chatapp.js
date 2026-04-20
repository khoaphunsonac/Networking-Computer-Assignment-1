(function () {
    "use strict";

    var STORAGE_USERNAME = "chat.username";
    var STORAGE_SELF_IP = "chat.selfIp";
    var STORAGE_SELF_P2P_PORT = "chat.selfP2pPort";

    var state = {
        username: "",
        channel: "general",
        peers: [],
        pollTimer: null,
        connected: false,
    };

    var chatPanel = document.getElementById("chatPanel");
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

    function defaultP2pPortFromHttpPort() {
        var httpPort = parseInt(window.location.port, 10);
        if (!Number.isNaN(httpPort) && httpPort > 0) {
            return String(httpPort + 1000);
        }
        return "3026";
    }

    async function loginToChat(username, selfIp, selfP2pPort, notifyOnSuccess) {
        var loginResult = await api("/login", "POST", { username: username });
        state.username = loginResult.peer_id || username;

        await api("/submit-info", "POST", {
            peer_id: "peer-" + window.location.port,
            ip: selfIp,
            port: selfP2pPort,
        });

        sessionStorage.setItem(STORAGE_USERNAME, state.username);
        sessionStorage.setItem(STORAGE_SELF_IP, selfIp);
        sessionStorage.setItem(STORAGE_SELF_P2P_PORT, String(selfP2pPort));

        activeChannelTitle.textContent = "General Chat";
        sessionInfo.textContent = "Logged as " + state.username + " • HTTP " + window.location.port;

        if (chatPanel) {
            chatPanel.classList.remove("hidden");
        }

        state.connected = true;
        await initialSync();
        startPolling();

        if (notifyOnSuccess) {
            notify("Đăng nhập thành công.");
        }
    }

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

        sessionStorage.removeItem(STORAGE_USERNAME);
        sessionStorage.removeItem(STORAGE_SELF_IP);
        sessionStorage.removeItem(STORAGE_SELF_P2P_PORT);

        if (chatPanel) {
            chatPanel.classList.add("hidden");
        }
        renderPeers();
        renderMessages([]);

        notify("Đã logout.");
        window.location.href = "/login.html";
    });

    window.addEventListener("beforeunload", function () {
        stopPolling();
    });

    (function initFromSession() {
        var savedUsername = sessionStorage.getItem(STORAGE_USERNAME) || "";
        var savedIp = sessionStorage.getItem(STORAGE_SELF_IP) || "127.0.0.1";
        var savedP2pPort = sessionStorage.getItem(STORAGE_SELF_P2P_PORT) || defaultP2pPortFromHttpPort();

        if (!savedUsername) {
            window.location.href = "/login.html";
            return;
        }

        loginToChat(savedUsername, savedIp, parseInt(savedP2pPort, 10), false).catch(function () {
            notify("Auto login không thành công. Vui lòng bấm Login lại.");
        });
    })();
})();