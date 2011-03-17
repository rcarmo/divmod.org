// -*- test-case-name: xmantissa.test.test_javascript -*-

// import MochiKit.DOM
// import Mantissa.LiveForm

/*
  This just does validation for Mantissa user-info-requiring signup right now,
  but the principles could hopefully be applied to other forms of LiveForm
  validation eventually.
 */

/*
  XXX TODO: I really want to say "package Mantissa.Validate" or something.
 */


/**
 * The various messages we display to the user. We have these out here so we
 * can keep English copy out of the code as much as possible.
 */
Mantissa.Validate.ERRORS = {
    'local-too-short': 'The local part is too short',
    'domain-too-short': 'The domain is too short',
    'address-too-short': 'Email address is too short',
    'input-empty': 'Input is empty',
    'password-weak': 'Password is too weak',
    'password-mismatch': 'Passwords do not match',
    'input-valid': 'Input is valid',
    'initial': 'Please enter your details',
    'unevaluated': 'Input not yet evaluated'
};



Mantissa.Validate.SignupForm = Mantissa.LiveForm.FormWidget.subclass(
    "Mantissa.Validate.SignupForm");


Mantissa.Validate.SignupForm.methods(
    function __init__(self, node, domain) {
        Mantissa.Validate.SignupForm.upcall(self, '__init__', node);
        self.domain = domain;
        self.inputCount = 0;
        var junk = self.gatherInputs();
        for (var yuck in junk) {self.inputCount++;}
        // minus one for domain, plus one for confirm...
        self.verifiedCount = 0;
        self.testedInputs = {};
        self.currentlyFocused = null;

        self.passwordInput = self.nodeByAttribute("name", "password");

        self.submitButton = self.nodeByAttribute("type", "submit");
    },


    /**
     * Return C{true} if the field has been evaluated and has valid input,
     * C{false} otherwise.
     */
    function isFieldValid(self, name) {
        if (name in self.testedInputs) {
            return self.testedInputs[name][0]
        }
        return false;
    },


    /**
     * Return the status message code for the given field. Returns 'unevaluated'
     * if the input has yet to be evaluated.
     */
    function getFieldStatusMessage(self, name) {
        if (name in self.testedInputs) {
            return self.testedInputs[name][1];
        }
        return 'unevaluated';
    },


    /**
     * Override submitSuccess to simply hide the progress message and show the
     * success message, since this form should not be submitted multiple
     * times, and the success message has instructions on the next step.
     */
    function submitSuccess(self, result) {
        self.hideProgressMessage();
        self.showSuccessMessage();
    },


    function mangleToLocalpart(self, txt) {
        /**
         * Replace any character not allowed in an email localpart
         * with an underscore.
         */
        txt = txt.replace(' ', '.');
        txt = txt.replace(/[ !%&\(\),:;<>\\\|@]/g, '_');
        return txt.toLowerCase();
    },


    function defaultUsername(self, inputnode) {
        /**
         * Create a username based on the first and last names entered.
         */
        if (inputnode.value.length == 0) {
            inputnode.value = self.mangleToLocalpart(
                self.nodeByAttribute("name", "realName").value);
        } else {
            self.updateStatus(inputnode);
        }
    },


    function verifyNotEmpty(self, inputnode) {
        /*
          This is bound using an athena handler to all the input nodes.

          We need to look for a matching feedback node for this input node.
         */
        self.verifyInput(inputnode, inputnode.value != '', "input-empty");
    },


    function verifyUsernameAvailable(self, inputnode) {
        var username = inputnode.value;
        var d = self.callRemote("usernameAvailable", username, self.domain);
        return d.addCallback(
            function (result) {
                var cond = result[0];
                var reason = result[1];
                self.verifyInput(inputnode, cond, reason);
            });
    },


    function passwordIsStrong(self, passwd) {
      return passwd.length > 4;
    },


    function verifyStrongPassword(self, inputnode) {
        self.verifyInput(inputnode, self.passwordIsStrong(inputnode.value),
                         "password-weak");
    },


    function verifyPasswordsMatch(self, inputnode) {
        if (self.passwordIsStrong(self.passwordInput.value)) {
            self.verifyInput(inputnode,
                             (self.isFieldValid('password')) &&
                             (inputnode.value === self.passwordInput.value),
                             "password-mismatch");
        }
    },


    function verifyValidEmail(self, inputnode) {
        var cond = null;
        var reason = null;
        var addrtup = inputnode.value.split("@");
        // require localpart *and* domain
        if (addrtup.length == 2) {
            var addrloc = addrtup[0];
            // localpart can't be empty
            if (addrloc.length > 0) {
                // domain can't be empty
                var addrdom = addrtup[1].split('.');
                if (addrdom.length >= 1) {
                    for (var i = 0; i < addrdom.length; i++) {
                        var requiredLength;
                        if (i === (addrdom.length - 1)) {
                            // TLDs are all 2 or more chars
                            requiredLength = 2;
                        } else {
                            // other domains can be one letter
                            requiredLength = 1;
                        }
                        if (addrdom[i].length < requiredLength) {
                            // WHOOPS
                            cond = false;
                            reason = "domain-too-short";
                            break;
                        } else {
                            // okay so far...
                            cond = true;
                        }
                    }
                }
            } else {
                cond = false;
                reason = "local-too-short";
            }
        } else {
            cond = false;
            reason = "address-too-short";
        }
        self.verifyInput(inputnode, cond, reason);
    },


    /**
     * Display the given message at the bottom of the signup form,
     * generally indicating some sort of validation error.
     */
    function setStatusMessage(self, message) {
        var node = self.nodeByAttribute('class', 'validation-message');
        if (message in Mantissa.Validate.ERRORS) {
            message = Mantissa.Validate.ERRORS[message];
        }
        MochiKit.DOM.replaceChildNodes(node, message);
    },


    function updateStatus(self, inputNode) {
        var message = 'input-valid';
        if (!self.isFieldValid(inputNode.name)) {
            message = self.getFieldStatusMessage(inputNode.name);
        }
        Divmod.msg(inputNode.name + ' => ' + message
                   + ' (' + self.isFieldValid(inputNode.name) + ')');
        if (self.currentlyFocused && self.currentlyFocused == inputNode.name) {
            self.setStatusMessage(message);
        }
    },


    function focus(self, inputNode) {
        self.currentlyFocused = inputNode.name;
        // XXX - probably want real dispatch here eventually -- jml
        if (inputNode.name == 'username') {
            self.defaultUsername(inputNode);
        }
        return self.updateStatus(inputNode);
    },


    function verifyInput(self, inputnode, condition, reason) {
        var statusNode = self._findStatusElement(inputnode);
        var status = '';
        var wasPreviouslyVerified = self.isFieldValid(inputnode.name);

        if (condition) {
            statusNode.src = '/Mantissa/images/ok-small.png';
        } else {
            statusNode.src = '/Mantissa/images/error-small.png';
            Divmod.msg(reason);
        }

        self.testedInputs[inputnode.name] = [condition, reason];
        Divmod.msg('Verified ' + inputnode.name + ': ['
                   + condition + ', ' + reason + ']');
        self.updateStatus(inputnode);

        if (condition != wasPreviouslyVerified) {
            if (condition) {
                self.verifiedCount++;
            } else {
                self.verifiedCount--;
            }
            if(self.verifiedCount === self.inputCount) {
                self.submitButton.removeAttribute("disabled");
            } else {
                self.submitButton.disabled = true;
            }
        }
    },


    function _findStatusElement(self, inputnode) {
        var fieldgroup = inputnode.parentNode;
        while (fieldgroup.className != "verified-field") {
            fieldgroup = fieldgroup.parentNode;
        }
        var theNodes = fieldgroup.childNodes;
        for (var maybeStatusNodeIdx in theNodes) {
            var maybeStatusNode = theNodes[maybeStatusNodeIdx];
            if (maybeStatusNode.className == "verify-status") {
                return maybeStatusNode;
            }
        }
    },


    function gatherInputs(self) {
        inputs = Mantissa.Validate.SignupForm.upcall(
            self, 'gatherInputs');
        delete inputs['confirmPassword'];
        delete inputs['__submit__'];
        // screw you, hidden fields!
        inputs['domain'] = [self.domain];
        return inputs;
    });

