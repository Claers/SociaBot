var channel_id = {};
var twitter_account_id = {};
var twitch_account_id = {};

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
        var server = el.parentElement.parentElement.parentElement.parentElement.parentElement;
        var server_id = server.id;
        for (i = 0; i < bot_user_guilds.length; i++) {
            if (server_id == bot_user_guilds[i]['server_id']) {
                server_data = bot_user_guilds[i];
            }
        }
        if (server_data['twitter_notification_enabled'] != null) {
            server.querySelector(".notif").checked = server_data['twitter_notification_enabled'];
            if (server_data['twitter_notification_enabled'] == true) {
                server.querySelector(".notif-text").innerHTML = "Activé";
            } else {
                server.querySelector(".notif-text").innerHTML = "Désactivé";
            }
        } else {
            server.querySelector(".notif").checked = false;
        }
        if (server_data['retweet_activated'] != null) {
            server.querySelector(".notif-retweet").checked = server_data['retweet_activated'];
            if (server_data['retweet_activated'] == true) {
                server.querySelector(".notif-retweet-text").innerHTML = "Activé";
            } else {
                server.querySelector(".notif-retweet-text").innerHTML = "Désactivé";
            }
        } else {
            server.querySelector(".notif-retweet").checked = false;
        }
        if (!(channel_id[server_id] == "None" || channel_id[server_id] == null)) {
            server.querySelector(".notif").disabled = false;
            server.querySelector(".notif-retweet").disabled = false;
        }

    }
    if (type == "channel") {
        var server = el.parentElement.parentElement.parentElement.parentElement.parentElement;
        var server_id = server.id;
        if (!(twitter_account_id[server_id] == "None" || twitter_account_id[server_id] == null)) {
            server.querySelector(".notif").disabled = false;
            server.querySelector(".notif-retweet").disabled = false;
        }
        if (!(twitch_account_id[server_id] == "None" || twitch_account_id[server_id] == null)) {
            server.querySelector(".notif").disabled = false;
        }
    }
    if (type == "twitch") {
        var bot_user_guilds = window.bot_user_guilds;
        var server_data = [];
        var server = el.parentElement.parentElement.parentElement.parentElement.parentElement;
        var server_id = server.id;
        for (i = 0; i < bot_user_guilds.length; i++) {
            if (server_id == bot_user_guilds[i]['server_id']) {
                server_data = bot_user_guilds[i];
            }
        }
        if (server_data['twitch_notification_enabled'] != null) {
            server.querySelector(".notif").checked = server_data['twitch_notification_enabled'];
            if (server_data['twitch_notification_enabled'] == true) {
                server.querySelector(".notif-text").innerHTML = "Activé";
            } else {
                server.querySelector(".notif-text").innerHTML = "Désactivé";
            }
        } else {
            server.querySelector(".notif").checked = false;
        }
        if (!(channel_id[server_id] == "None" || channel_id[server_id] == null)) {
            server.querySelector(".notif").disabled = false;
        }
    }

    if (type == "unselect") {
        var server = el.parentElement.parentElement.parentElement.parentElement.parentElement;
        server.querySelector(".notif").disabled = true;
        try {
            server.querySelector(".notif-retweet").disabled = true;
        } catch (error) {

        }

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

document.addEventListener('DOMContentLoaded', () => {
    (document.querySelectorAll('.notification .delete') || []).forEach(($delete) => {
        $notification = $delete.parentNode;
        $delete.addEventListener('click', () => {
            $notification.parentNode.removeChild($notification);
        });
    });
});