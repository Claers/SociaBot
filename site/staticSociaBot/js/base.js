function toggleDropdown(el) {
    el.parentElement.parentElement.classList.toggle("is-active");
}

function contentSelect(el, type) {
    el.parentElement.parentElement.parentElement.children[0].children[0].children[0].innerHTML = el.innerHTML
        .trim();
    if (type == "exclude") {
        botExcludeUrl(el.parentElement.parentElement.parentElement.parentElement.children[2], el.innerHTML);
    }
    if (type == "twitter") {
        var bot_user_guilds = window.bot_user_guilds;
        var server_data = [];
        var server = el.parentElement.parentElement.parentElement.parentElement;
        var server_id = server.className.split(' ')[1];
        for (i = 0; i < bot_user_guilds.length; i++) {
            if (server_id == bot_user_guilds[i]['id']) {
                server_data = bot_user_guilds[i]
            }
        }
        if (server_data['twitter_notification_enabled'] != null) {
            server.children[3].children[1].checked = server_data['twitter_notification_enabled'];
            if (server_data['twitter_notification_enabled'] == true) {
                server.children[3].children[2].innerHTML = "Activé";
            } else {
                server.children[3].children[2].innerHTML = "Désactivé";
            }
        } else {
            server.children[3].children[1].checked = false;
        }
        if (!(channel_id == "None" || channel_id == null)) {
            server.children[3].children[1].disabled = false;
        }
    }
    if (type == "channel") {
        var server = el.parentElement.parentElement.parentElement.parentElement;
        if (!(twitter_account_id == "None" || twitter_account_id == null)) {
            server.children[3].children[1].disabled = false;
        }

    }
    if (type == "unselect") {
        var server = el.parentElement.parentElement.parentElement.parentElement;
        server.children[3].children[1].checked = false;
        server.children[3].children[1].disabled = true;
        server.children[3].children[2].innerHTML = "Désactivé";
    }
    toggleDropdown(el.parentElement);
}

function changeText(el) {
    if (el.checked) {
        el.parentElement.children[2].innerHTML = "Activé"
    } else {
        el.parentElement.children[2].innerHTML = "Désactivé"
    }
}

var twitter_account_id = null;
var channel_id = null;

function sendJsonData(el) {
    var i;
    var jsonData = [];
    var servers = window.servers;
    el.setAttribute("disabled", true);
    for (i = 0; i < servers.length; i++) {
        server_id = servers[i].className.split(' ')[1];
        notif_on = servers[i].children[3].children[1].checked;
        jsonData.push({
            'server_id': server_id,
            'twitter_account_id': twitter_account_id,
            'notif_on': notif_on,
            'notif_id': channel_id
        })
    }
    $.ajax({
        type: 'POST',
        contentType: 'application/json',
        data: JSON.stringify(jsonData),
        dataType: 'json',
        url: '/twitter_update_infos/',
    });
    setTimeout(function () {
        location.reload();
    }, 1000);

}

function openServer(server_name) {
    var i;
    var x = document.getElementsByClassName("twitter-update");
    for (i = 0; i < x.length; i++) {
        x[i].style.display = "none";
    }
    document.getElementById(server_name).style.display = "block";
}

document.addEventListener('DOMContentLoaded', () => {
    (document.querySelectorAll('.notification .delete') || []).forEach(($delete) => {
        $notification = $delete.parentNode;
        $delete.addEventListener('click', () => {
            $notification.parentNode.removeChild($notification);
        });
    });
});