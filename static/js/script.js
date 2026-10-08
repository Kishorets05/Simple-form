function showRegister() {
    document.getElementById("registerSection").classList.remove("hidden");
    document.getElementById("loginSection").classList.add("hidden");

    document.getElementById("tabRegisterBtn").classList.add("active");
    document.getElementById("tabLoginBtn").classList.remove("active");
}

function showLogin() {
    document.getElementById("registerSection").classList.add("hidden");
    document.getElementById("loginSection").classList.remove("hidden");

    document.getElementById("tabRegisterBtn").classList.remove("active");
    document.getElementById("tabLoginBtn").classList.add("active");
}

function confirmDelete() {
    return confirm("Are you sure you want to delete your account?");
}