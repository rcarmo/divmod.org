// import Mantissa

Mantissa.Authentication = Nevow.Athena.Widget.subclass("Mantissa.Authentication");

Mantissa.Authentication.methods(
    function submitNewPassword(self, form) {
        if (form.newPassword.value != form.confirmPassword.value) {
            alert('Passwords do not match.  Try again.');
        } else {
            var curPass = null;
            if (form.currentPassword) {
                curPass = form.currentPassword.value;
                form.currentPassword.value = '';
            }

            var newPass = form.newPassword.value;
            form.newPassword.value = form.confirmPassword.value = '';

            var D = self.callRemote('changePassword', curPass, newPass);
            D.addBoth(alert);
        }
    },

    function cancel(self, sessionId) {
        self.callRemote('cancel', sessionId).addBoth(alert);
    });

