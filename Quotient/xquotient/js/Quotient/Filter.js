// import Mantissa.LiveForm
// import Quotient
// import Quotient.Common

Quotient.Filter.RuleWidget = Mantissa.LiveForm.FormWidget.subclass("Quotient.Filter.RuleWidget");
Quotient.Filter.RuleWidget.methods(
    function submit(self) {
        Quotient.Filter.RuleWidget.upcall(self, 'submit');
        return false;
    });

Quotient.Filter.HamConfiguration = Nevow.Athena.Widget.subclass("Quotient.Filter.HamConfiguration");
Quotient.Filter.HamConfiguration.methods(
    function retrain(self) {
        self.callRemote('retrain').addCallback(function(result) {
            self.node.appendChild(document.createTextNode('Training reset.'));
        }).addErrback(function(err) {
            self.node.appendChild(document.createTextNode('Error: ' + err.description));
        });
        return false;
    },

    /**
     * Show help text
     */
    function showHelpText(self) {
        var htnode = self.firstNodeByAttribute("class", "spam-filter-help-text");
        Quotient.Common.Util.showNodeAsDialog(htnode);
    },

    function reclassify(self) {
        self.callRemote('reclassify').addCallback(function(result) {
            self.node.appendChild(document.createTextNode('Beginning reclassification.'));
        }).addErrback(function(err) {
            self.node.appendChild(document.createTextNode('Error: ' + err.description));
        });
        return false;
    });
