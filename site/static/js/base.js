function toggleDropdown(el) {
    el.parentElement.parentElement.classList.toggle("is-active");
}

function contentSelect(el, type) {
    el.parentElement.parentElement.parentElement.children[0].children[0].children[0].innerHTML = el.innerHTML
        .trim();
    if (type == "exclude") {
        botExcludeUrl(el.parentElement.parentElement.parentElement.parentElement.children[2], el.innerHTML);
    }
    toggleDropdown(el.parentElement);
}

var twitter_account_id;

function sendJsonData() {
    var twitter = document.getElementById('twitter');
    var server = twitter.children[0].children;
    var i;
    var jsonData = [];
    console.log(twitter.children[0].children);
    for (i = 0; i < twitter.children[0].children.length; i++) {
        server_id = server[i].className.split(' ')[1];
        print(server[i].children[1].children[1].children[0])
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