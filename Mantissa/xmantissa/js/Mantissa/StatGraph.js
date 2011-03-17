// import MochiKit
// import MochiKit.Base
// import MochiKit.Iter
// import MochiKit.DOM
// import PlotKit.Base
// import PlotKit.Layout
// import PlotKit.Canvas
// import PlotKit.SweetCanvas
// import Mantissa

Mantissa.StatGraph.Pie = Divmod.Class.subclass();
/* Mantissa.StatGraph.Pie: 
   I represent a pie chart drawn with PlotKit. 
*/
Mantissa.StatGraph.Pie.methods(
    function __init__(self, canvas) {
        /** canvas: a canvas DOM node. */
        self.canvas = canvas;
        canvas.height = 900;
        canvas.width = 900;

        self.layout = new PlotKit.Layout("pie");

        self.graph = new PlotKit.SweetCanvasRenderer(self.canvas, self.layout, {'axisLabelWidth':160});
    },

    function draw(self, slices) {
        /** Actually render the piechart.
            slices: a pair of lists: labels for slices (strings), and slice values (floats).
         */
        self.layout.options.xTicks = MochiKit.Base.map(function(L, val) { return {"label": L, v: val};}, slices[0],
                                                       MochiKit.Iter.range(slices[0].length));
        self.layout.addDataset("data", MochiKit.Base.zip(MochiKit.Iter.range(slices[1].length), slices[1]));
        self.layout.evaluate();
        self.graph.clear();
        self.graph.render();
    });

Mantissa.StatGraph.GraphData = Divmod.Class.subclass();
/** Mantissa.StatGraph.GraphData:
    I represent a line chart drawn with PlotKit.
 */
Mantissa.StatGraph.GraphData.methods(
    function __init__(self, canvas) {
        /** canvas: a canvas DOM node. */
        self.plots = {}
        self.xs = null;
        self.canvas = canvas;
        var xticks = [];
        self.layout = new PlotKit.Layout("line", {xTicks: xticks});
        self.graph = new PlotKit.SweetCanvasRenderer(self.canvas, self.layout, {});
    },

    function addPlot(self, name, xs, ys) {
        /** Add a line to be plotted on this graph.
            name: An identifier for this data set.

            xs: A list of X-axis labels (strings). If adding more than one
            plot, this list needs to be equal to the current X axis.

            ys: A list of Y values for this plot (floats).
        */
        if (self.xs == null) {
            self.xs = xs;
        } else if (!MochiKit.Base.arrayEqual(xs, self.xs)) {
            throw TypeError(name + "has different timescale from existing plots");
        }
        self.plots[name] = ys;
    },
    function _updateXTicks(self) {
        var allXTicks = MochiKit.Base.map(function(L, val) { return {"label": L, v: val};}, self.xs, 
                                          MochiKit.Iter.range(self.xs.length));
        // XXX find a better way to do this maybe?
        var len = allXTicks.length;
        self.layout.options.xTicks.length = 0;
        if (len > 5) {
            for (var i = 0; i < len; i += Math.floor(len/4)) {
                self.layout.options.xTicks.push(allXTicks[i]);
            }
        } else {
            self.layout.options.xTicks = allXTicks;
        }
    },
    function draw(self) {
        /** Draw this graph on its canvas. */
        var doPlots = function(name, plot) {
            self.layout.addDataset(name, MochiKit.Base.map(null, MochiKit.Iter.range(self.xs.length),
                                                           plot));
        };
        MochiKit.Iter.exhaust(MochiKit.Iter.applymap(doPlots, MochiKit.Base.items(self.plots)));
        self._updateXTicks();
        self.layout.evaluate();
        self.graph.clear();
        self.graph.render();
    });

Mantissa.StatGraph.StatGraph = Nevow.Athena.Widget.subclass("Mantissa.StatGraph.StatGraph");
/** Mantissa.StatGraph.StatGraph: I control the display of statistics graphs on
    the Stats page of the Mantissa admin console, and receive updates from
    stats collectors on the server.
*/

Mantissa.StatGraph.StatGraph.methods(
    function __init__(self, node) {
        Mantissa.StatGraph.StatGraph.upcall(self, '__init__', node);
        self.graphs = {};
        self.pieMode = "pie";
        self.pie = null;
        self.callRemote('getGraphNames').addCallback(
            function (names) {
                var graphSelector = MochiKit.DOM.SELECT({}, MochiKit.Iter.chain([MochiKit.DOM.OPTION({},""),
                                                                                 MochiKit.DOM.OPTION({"value": "pie"},
                                                                                                     "Query time piechart")],
                                                                                MochiKit.Base.map(
                                                                                    function (name) {
                                                                                        return MochiKit.DOM.OPTION(
                                                                                        {"value": name[0]},
                                                                                        name[1])
                                                                                            }, names)));
                graphSelector.onchange = function () {
                    var name = graphSelector[graphSelector.selectedIndex].value;
                    var desc = graphSelector[graphSelector.selectedIndex].text;
                    if (name == "pie") {
                        self.callRemote('buildPie').addCallback(function(slices) {self.drawPie(slices)});
                    } else if (name != "") {
                        self.callRemote('addStat',name).addCallback(
                            function (data) { node.appendChild(self.newGraph(name, desc, data));});
                    }};
                self.node.appendChild(graphSelector);
            });
    },
    function drawPie(self, slices) {

        /** Draw a pie chart with a selector for the time period it represents,
            and a toggle to show a table of the same data instead.
        */
        var g = new Mantissa.StatGraph.Pie(self._newCanvas("Pie!"));
        self.pie = g;
        var p = g.canvas.parentNode;
        var details = MochiKit.DOM.A({"onclick": function () { self.togglePieOrTable(self.pie, p)},
                                          "class": "sublink", "style": "cursor: pointer"},
                                     "Toggle Table/Pie");
        g.canvas.parentNode.insertBefore(details, g.canvas);
        var periodSelector = MochiKit.DOM.SELECT({}, MochiKit.Base.map(
                                                     function(x) {return MochiKit.DOM.OPTION({"value":x[1]}, x[0])},
                                                     [["60 minutes", 60], ["30 minutes", 30], ["15 minutes", 15]]));
        periodSelector.onchange = function () {
            self.callRemote('setPiePeriod',
                            periodSelector[periodSelector.selectedIndex].value);
            self.callRemote('buildPie').addCallback(
                function (slices) {self.slices = slices;
                if (self.pieMode == "pie") {
                    g.draw(slices);
                } else {
                    p.removeChild(p.lastChild);
                    self.table = self.makeSliceTable();
                    p.appendChild(self.table);
                }})};
        g.canvas.parentNode.insertBefore(periodSelector, g.canvas);
        self.slices = slices;
        g.draw(slices);
    },
    function newGraph(self, name, desc, data) {
        /** Add a new line graph to the page.
            name: An identifier for this graph.
            desc: A title to display above the graph.
            data: A pair of lists, containing X-axis labels and Y-axis data points.
        */
        var canvas = self._newCanvas(desc);
        var graphdata = Mantissa.StatGraph.GraphData(canvas);
        graphdata.addPlot(name, data[0], data[1]);
        graphdata.draw();
        self.graphs[name] = graphdata;
    },
    function makeSliceTable(self) {
        var pairs = MochiKit.Base.map(function (pair) { return [MochiKit.DOM.TD({}, pair[0]),
                                                                MochiKit.DOM.TD({}, pair[1])] },
                                      MochiKit.Base.zip(self.slices[0], self.slices[1]));
        var trs = MochiKit.Base.map(MochiKit.Base.partial(MochiKit.DOM.TR, null), pairs);
        var tbody = MochiKit.DOM.TBODY({}, trs);
        var t= MochiKit.DOM.TABLE({}, [MochiKit.DOM.THEAD({}, MochiKit.DOM.TR({},
                                                                              MochiKit.DOM.TD({}, "Source"),
                                                                              MochiKit.DOM.TD({}, "Time"))),
                                       tbody]);
        return t;
    },
    function togglePieOrTable(self, g, p) {
        if (self.pieMode == "pie") {
            g.graph.clear();
            p.removeChild(g.canvas);
            t = self.makeSliceTable();
            p.appendChild(t);
            self.table = t;
            self.pieMode = "table";
            self.pie = null;
        } else {
            p.removeChild(p.lastChild); // that's the table, right?
            var canvas = document.createElement('canvas');
            p.appendChild(canvas);
            self.pie =  new Mantissa.StatGraph.Pie(canvas);
            self.pie.draw(self.slices);
            self.pieMode = "pie";
            self.table = null;
        }
    },

    function _newCanvas(self, title) {
        var container = document.createElement('div');
        var t = document.createElement('div');
        var container2 = document.createElement('div');
        var canvas = document.createElement("canvas");
        t.appendChild(document.createTextNode(title));
        container.appendChild(t);
        container.appendChild(container2);
        container2.appendChild(canvas);
        container2.style.width = "500px";
        t.style.textAlign = "center";
        t.style.width = "500px";
        canvas.width = 500;
        canvas.height = 200;
        self.node.appendChild(container);
        return canvas;
    },

    function update(self, time, updates) {
        /** Add a new data point to the displayed graphs.

        time: The time associated with this datum.
        updates: A mapping of graph identifiers to new data points.
        */

        var ps = MochiKit.Iter.chain.apply(MochiKit.Iter.chain,
                                           MochiKit.Base.map(function (g) {return MochiKit.Base.items(g[1].plots)},
                                                             MochiKit.Base.items(self.graphs)));
        MochiKit.Iter.exhaust(MochiKit.Iter.applymap(function (plotName, ys) {
            ys.push(updates[plotName]);
            if (ys.length > 60) {
                ys.shift();
            }
        }, ps));
        MochiKit.Base.map(function (x) {
            var g = x[1];
            g.xs.push(time);
            if (g.xs.length > 60) {
                g.xs.shift();
            };
            g.draw();
        }, MochiKit.Base.items(self.graphs));
    },

    function updatePie(self, slices) {
        /** Update the pie chart (if displayed)
            with these new slices.
        */
        if (self.pie == null) {
            return;
        }
        self.slices = slices;
        if (self.pieMode == "pie") {
            self.pie.draw(slices);
        } else {
            var oldtable = self.table;
            self.table = self.makeSliceTable();
            oldtable.parentNode.replaceChild(self.table, oldtable);
        }
    });
