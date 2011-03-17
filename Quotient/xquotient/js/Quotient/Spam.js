// import Mantissa.LiveForm

Quotient.Spam.PostiniSettings = Mantissa.LiveForm.FormWidget.subclass("Quotient.Spam.PostiniSettings");
/**
 * FormWidget used by L{xquotient.spam.HamFilterFragment} for editing Postini
 * settings.
 */
Quotient.Spam.PostiniSettings.methods(
    /**
     * When the form is submitted successfully, populate the form's fields with
     * the new values.
     */
    function submitSuccess(self, result) {
        var formValues = self.gatherInputs();
        var d = Quotient.Spam.PostiniSettings.upcall(self, "submitSuccess",
                                                     result);
        return d.addCallback(
            function (result) {
                self.setInputValues(formValues);
                return result;
            });
    });
