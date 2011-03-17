
// import Mantissa
// import Mantissa.LiveForm

Mantissa.Offering.UninstalledOffering = Nevow.Athena.Widget.subclass('Mantissa.Offering.UninstalledOffering');
Mantissa.Offering.UninstalledOffering.methods(
    function notify(self, message, className, duration) {
        var node = document.createElement('div');
        node.className = className;
        node.appendChild(document.createTextNode(message));
        document.body.appendChild(node);
        self.callLater(duration, function() { document.body.removeChild(node); });
    },

    function install(self) {
        self.node.className = 'installing';
        var d = self.callRemote('install', {});
        d.addCallbacks(
            function(result) {
                self.notify('Installed', 'install-succeeded', 1);
                self.node.className = 'installed';
                self.node.onclick = null;
            },
            function(err) {
                self.notify('Failure: ' + err, 'install-failed', 5);
                self.node.className = 'uninstalled';
            });
    });
