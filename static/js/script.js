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

function phone() {
    const phoneInput = document.getElementById("reg-phone");

    if (!phoneInput) return;

    phoneInput.addEventListener("invalid", function () {
        if (phoneInput.validity.valueMissing) {
            phoneInput.setCustomValidity(
                "Phone number is required."
            );
        } else if (phoneInput.validity.patternMismatch) {
            phoneInput.setCustomValidity(
                "Enter Phone number in correct format,Example: 9876543210"
            );
        }
    });

    phoneInput.addEventListener("input", function () {
        phoneInput.setCustomValidity("");
    });
}
document.addEventListener("DOMContentLoaded", phone);


function mail() {
    const email = document.getElementById("reg-email");
    if (!email) return;

    const emailPattern =
        /^[a-zA-Z0-9_%+-]+(\.[a-zA-Z0-9_%+-]+)*@[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?)*\.[a-zA-Z]{2,}$/;

    function validateEmail() {
        const value = email.value.trim();

        if (email.validity.valueMissing || value === "") {
            email.setCustomValidity("Email is required.");
        } else if (!emailPattern.test(value)) {
            // This catches brow@gmailcom instantly
            email.setCustomValidity("Invalid email. Example: brown@gmail.com");
        } else {
            // Clear the error if it passes your strict regex
            email.setCustomValidity("");
        }
    }

    // Check validation in real-time as they type
    email.addEventListener("input", validateEmail);
    
    // Also catch it if they trigger native validation mechanics
    email.addEventListener("invalid", validateEmail);
}

document.addEventListener("DOMContentLoaded", function () {
    mail();
});



function password() {
    const pass = document.getElementById("reg-password");

    if (!pass) return;

    function validatePassword() {
        const value = pass.value;

        if (value === "") {
            pass.setCustomValidity("Password is required.");
        } else if (value.length < 8) {
            pass.setCustomValidity(
                "Password must contain at least 8 characters."
            );
        } else if (!/[A-Z]/.test(value)) {
            pass.setCustomValidity(
                "Password must contain at least one uppercase letter (A-Z)."
            );
        } else if (!/[a-z]/.test(value)) {
            pass.setCustomValidity(
                "Password must contain at least one lowercase letter (a-z)."
            );
        } else if (!/[0-9]/.test(value)) {
            pass.setCustomValidity(
                "Password must contain at least one digit (0-9)."
            );
        } else if (!/[^A-Za-z0-9]/.test(value)) {
            pass.setCustomValidity(
                "Password must contain at least one special character."
            );
        } else {
            pass.setCustomValidity("");
        }
    }

    pass.addEventListener("input", validatePassword);
    pass.addEventListener("invalid", validatePassword);
}

document.addEventListener("DOMContentLoaded", function () {
    password();
});


