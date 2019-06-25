function sendJsonData(el) {
    var i;
    var jsonData = [];
    var servers = window.servers;
    el.setAttribute("disabled", true);
    for (i = 0; i < servers.length; i++) {
        server_id = servers[i].id;
        notif_on = servers[i].querySelector(".notif").checked;
        jsonData.push({
            'server_id': server_id,
            'twitch_account_id': twitch_account_id[server_id],
            'notif_on': notif_on,
            'notif_id': channel_id[server_id]
        })
    }
    $.ajax({
        type: 'POST',
        contentType: 'application/json',
        data: JSON.stringify(jsonData),
        dataType: 'json',
        url: '/sociabot/twitch_update_info',
    });
    setTimeout(function () {
        location.reload();
    }, 1000);
}

function openServer(server_id, el) {
    var i;
    var server = document.getElementsByClassName("twitch-update");
    var server_list = document.getElementsByClassName("server-list");
    for (i = 0; i < server.length; i++) {
        server[i].style.display = "none";
    }
    for (i = 0; i < server_list.length; i++) {
        server_list[i].classList.remove('is-active');
    }
    el.parentElement.classList.add('is-active');
    document.getElementById(server_id).style.display = "block";
}