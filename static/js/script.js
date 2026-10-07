function showRegister() {

    document
        .getElementById("register")
        .classList.remove("hidden");

    document
        .getElementById("login")
        .classList.add("hidden");
}


function showLogin() {

    document
        .getElementById("login")
        .classList.remove("hidden");

    document
        .getElementById("register")
        .classList.add("hidden");
}


function confirmDelete() {

    return confirm(
        "Are you sure you want to delete your account?"
    );
}