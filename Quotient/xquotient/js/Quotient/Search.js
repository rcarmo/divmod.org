/**
 * This module is a half-measure.  Ideally, the quotient message
 * list would be embedded in the search results page.
 */

// import Mantissa.ScrollTable

Quotient.Search.SearchResults = Mantissa.ScrollTable.ScrollingWidget.subclass(
                                    'Quotient.Search.SearchResults');

Quotient.Search.SearchResults.methods(
    function __init__(self, node, metadata) {
        self.columnAliases = {receivedWhen: "Date", senderDisplay: "From"};
        Quotient.Search.SearchResults.upcall(self, "__init__", node, metadata);
        self.node.style.margin = "4px";
    },

    /**
     * Override L{Mantissa.ScrollTable.ScrollingWidget.skipColumn}
     * so the "read" column doesn't get displayed -- we represent
     * the value of the column by having the row text be bold/unbold,
     * rather than showing the value directly
     */
    function skipColumn(self, colname) {
        return colname == "read";
    },

    /**
     * Override L{Mantissa.ScrollTable.ScrollingWidget.makeRowElement}
     * to set the appropriate styles on rows that represent read/unread
     * messages
     */
    function makeRowElement(self, rowOffset, rowData, cells) {
        var node = Quotient.Search.SearchResults.upcall(
                        self, "makeRowElement", rowOffset, rowData, cells);

        if(!rowData["read"]) {
            node.setAttribute("style", node.style + ";font-weight:bold");
        }
        return node;
    });
