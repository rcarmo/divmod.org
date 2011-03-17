function signup(node) {
    var inputEmail = node.input_email.value;

    /* Do some very rudamentary input checking */
    var splatIndex = inputEmail.indexOf('@');
    if (splatIndex == -1 || inputEmail.length < 3) {
        alert('Please enter an email address.');
        return;
    }

    var signupStatus = document.getElementById('signup-status');
    signupStatus.innerHTML = 'THINKING';
    node.onsubmit = function() {
        alert('Signup in progress...');
        return false;
    }

    var port;
    if (this.location.port == null) {
        port = 80;
    } else {
        port = this.location.port;
    }
    var issueDeferred = server.callRemote('issueTicket', this.location, inputEmail);
    issueDeferred.addCallback(function(result) {
        signupStatus.innerHTML = result;
    });
    issueDeferred.addErrback(function(err) {
        signupStatus.innerHTML = 'An error has occurred: ' + new String(err);
    });
}
