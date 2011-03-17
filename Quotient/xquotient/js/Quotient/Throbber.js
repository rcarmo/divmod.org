
// import Divmod

/**
 * A visual progress indicator.
 */
Quotient.Throbber.Throbber = Divmod.Class.subclass('Quotient.Throbber.Throbber');
Quotient.Throbber.Throbber.methods(
    /**
     * @param node: A DOM node which will be displayed when the throbber is
     * started.
     */
    function __init__(self, node) {
        self.node = node;
    },

    /**
     * Start indicating progress.
     */
    function startThrobbing(self) {
        self.node.style.display = '';
    },

    /**
     * Stop indicating progress.
     */
    function stopThrobbing(self) {
        self.node.style.display = 'none';
    });
