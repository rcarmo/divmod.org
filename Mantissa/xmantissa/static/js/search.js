
// import Nevow
// import Nevow.Athena

// import Mantissa

Mantissa.Search.Search = Nevow.Athena.Widget.subclass('Mantissa.Search.Search');
Mantissa.Search.Search.methods(
    function __init__(self, node) {
        Mantissa.Search.Search.upcall(self, '__init__', node);
        self.resultsContainer = self.nodeByAttribute('class', 'results-container');
    },

    function search(self, term) {
        self.callRemote('search', term).addCallback(function(result) {
            Divmod.Runtime.theRuntime.setNodeContent(
                self.resultsContainer, result);
        });
    });
