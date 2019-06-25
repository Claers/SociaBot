function sendJsonData(el) {
    var i;
    var jsonData = [];
    var servers = window.servers;
    el.setAttribute("disabled", true);
    for (i = 0; i < servers.length; i++) {
        server_id = servers[i].id;
        notif_on = servers[i].querySelector(".notif").checked;
        retweet_notif_on = servers[i].querySelector(".notif-retweet").checked;
        jsonData.push({
            'server_id': server_id,
            'twitter_account_id': twitter_account_id[server_id],
            'notif_on': notif_on,
            'notif_id': channel_id[server_id],
            'retweet_notif_on': retweet_notif_on,
        })
    }
    $.ajax({
        type: 'POST',
        contentType: 'application/json',
        data: JSON.stringify(jsonData),
        dataType: 'json',
        url: '/sociabot/twitter_update_infos/',
    });
    setTimeout(function () {
        location.reload();
    }, 1000);

}

function openServer(server_id, el) {
    var i;
    var server = document.getElementsByClassName("twitter-update");
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