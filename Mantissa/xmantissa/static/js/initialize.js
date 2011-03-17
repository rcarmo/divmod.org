function checkPasswords(form) {
    if (form.password.value != form.confirm.value) {
        alert("Passwords don't match!  Try again.");
        form.password.value = form.confirm.value = '';
        form.password.focus();
        return false;
    } else {
        return true;
    }
}
