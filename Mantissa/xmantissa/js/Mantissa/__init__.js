
// import Nevow.Athena

Mantissa.InputHistory = Divmod.Class.subclass('Mantissa.InputHistory');
Mantissa.InputHistory.method(
    function __init__(self) {
        self.lines = [''];
        self.historyPosition = 0;
    });

Mantissa.InputHistory.method(
    function goForward(self) {
        if (self.historyPosition == self.lines.length - 1) {
            if (self.lines[self.lines.length - 1] != '') {
            }
        }
    });

Mantissa.InterpreterWidget = Nevow.Athena.Widget.subclass('Mantissa.InterpreterWidget');
Mantissa.InterpreterWidget.method(
    function __init__(self, node) {
        Mantissa.InterpreterWidget.upcall(self, '__init__', node);

        self.state = 'idle';
        self.inputLine = '';
        self.cursorPosition = 0;
        self.requiresMoreInput = false;

        self.replDisplay = self.nodeByAttribute('class', 'repl-display');
        self.replInput = self.nodeByAttribute('class', 'repl-input');
        self.replCursor = self.nodeByAttribute('class', 'repl-cursor');

        self.eventMethods = self.nodeByAttribute('class', 'event-methods');
        self.eventAttrs = self.nodeByAttribute('class', 'event-attributes');

        document.addEventListener('keypress',
                                  function(event) {
                                      self.onKeyPress(event);
                                      return false;
                                  }, true);

        self.setupInputPrompt();
        self.positionInputCursor();
    });

Mantissa.InterpreterWidget.method(
    function onKeyPress(self, event) {
        if (self.state == 'evaluating') {
            return;
        }
//         event.initKeyEvent(
//             event.type,

//         event.currentTarget = self.superHack;
//         return;

//         var methods = [];
//         var attributes = [];
//         for (var i in event) {
//             if (event[i] instanceof Function) {
//                 methods.push(i);
//             } else {
//                 attributes.push([[i, event[i]]]);
//             }
//         }
//         self.eventMethods.innerHTML = methods.toSource();
//         self.eventAttrs.innerHTML = attributes.toSource();

        var keyCode = event.keyCode;
        var charCode = event.charCode;

        if (keyCode == event.DOM_VK_BACK_SPACE ||
            keyCode == event.DOM_VK_LEFT ||
            keyCode == event.DOM_VK_RIGHT ||
            keyCode == event.DOM_VK_UP ||
            keyCode == event.DOM_VK_DOWN ||
            keyCode == event.DOM_VK_TAB ||
            keyCode == event.COM_VK_SPACE ||
            charCode == ' '.charCodeAt(0) ||
            charCode == "'".charCodeAt(0)) {

            event.stopPropagation();
            event.preventDefault();
            event.preventBubble();
            event.cancelBubble = true;
        }

        switch (keyCode) {

        case event.DOM_VK_RETURN:
            self.state = 'evaluating';
            self.evaluateInputLine().addCallback(function(ignored) { self.state = 'idle'; });
            break;

        case event.DOM_VK_BACK_SPACE:
            self.removeInputCharacter();
            break;

        case event.DOM_VK_LEFT:
            if (self.cursorPosition > 0) {
                self.cursorPosition -= 1;
                self.positionInputCursor();
            }
            break;

        case event.DOM_VK_RIGHT:
            if (self.cursorPosition < self.inputLine.length) {
                self.cursorPosition += 1;
                self.positionInputCursor();
            }
            break;

        case event.DOM_VK_HOME:
            if (self.cursorPosition > 0) {
                self.cursorPosition = 0;
                self.positionInputCursor();
            }
            break;

        case event.DOM_VK_END:
            if (self.cursorPosition < self.inputLine.length) {
                self.cursorPosition = self.inputLine.length;
                self.positionInputCursor();
            }
            break;

        case event.DOM_VK_UP:
            if (self.historyPosition > 0) {
                self.historyPosition -= 1;
            }
            break;

        case event.DOM_VK_TAB:
            var count = 4 - (self.inputLine.length % 4);
            if (count == 0) {
                count = 4;
            }
            for (var i = 0; i < count; ++i) {
                self.addInputCharacter(' ');
            }
            break;

        default:
            var ch = String.fromCharCode(charCode);
            if (self.characterOkay(ch)) {
                self.addInputCharacter(ch);
            }
            break;
        }
    });

Mantissa.InterpreterWidget.method(
    function characterOkay(self, ch) {
        return (
            'ABCDEFGHIJKMLNOPQRSTUVWXYZ' +
            'abcdefghijklmnopqrstuvwxyz' +
            '0123456789' +
            ' !"#$%&()*+,-./:;<=>?@' +
            '[]^_`{|}~' +
            "'" +
            '\\').indexOf(ch) != -1;
    });

Mantissa.InterpreterWidget.method(
    function evaluateInputLine(self) {
        var inputLine = self.clearInputLine();
        if (self.requiresMoreInput) {
            var pfx = '...&nbsp;';
        } else {
            var pfx = '>>>&nbsp;';
        }
        self.addOutputLine(pfx + inputLine);
        var d = self.callRemote('evaluateInputLine', inputLine);
        d.addCallback(function(more) {
            self.requiresMoreInput = more;
            self.setupInputPrompt();
            self.positionInputCursor();
        });
        return d;
    });

Mantissa.InterpreterWidget.method(
    function _escapeForHTML(self, s) {
        return s.replace(/  /g, '&nbsp; ').replace(/</g, '&lt;').replace(/\n/g, '<br />');
    });

Mantissa.InterpreterWidget.method(
    function addOutputLine(self, line) {
        self.addOutputLines([line]);
    });

Mantissa.InterpreterWidget.method(
    function addOutputLines(self, outputLines) {
        for (var i = 0; i < outputLines.length; ++i) {
            if (outputLines[i].length || i != outputLines.length - 1) {
                var d = document.createElement('div');
                d.innerHTML = self._escapeForHTML(outputLines[i]);
                self.replDisplay.insertBefore(d, self.replInput);
            }
        }
        self.replInput.scrollIntoView();
    });

Mantissa.InterpreterWidget.method(
    function clearInputLine(self) {
        var inputLine = self.inputLine;
        self.inputLine = '';
        self.replInput.innerHTML = '';
        self.cursorPosition = 0;
        return inputLine;
    });

Mantissa.InterpreterWidget.method(
    function setupInputPrompt(self) {
        if (self.requiresMoreInput) {
            self.replInput.innerHTML = '...&nbsp;';
        } else {
            self.replInput.innerHTML = '&gt;&gt;&gt;&nbsp;';
        }
    });

Mantissa.InterpreterWidget.method(
    function positionInputCursor(self) {
        var pfx = '&nbsp;&nbsp;&nbsp;&nbsp;';
        for (var i = 0; i < self.cursorPosition; ++i) {
            pfx += '&nbsp;';
        }
        self.replCursor.innerHTML = pfx + '^';
    });

Mantissa.InterpreterWidget.method(
    function setInputLine(self, line) {
        self.inputLine = line;
        self.setupInputPrompt();
        self.replInput.innerHTML += self._escapeForHTML(line);
    });

Mantissa.InterpreterWidget.method(
    function addInputCharacter(self, ch) {
        self.setInputLine(
            self.inputLine.slice(0, self.cursorPosition) +
            ch +
            self.inputLine.slice(self.cursorPosition, self.inputLine.length));
        self.cursorPosition += 1;
        self.positionInputCursor();
    });

Mantissa.InterpreterWidget.method(
    function removeInputCharacter(self) {
        if (self.inputLine.length) {
            self.setInputLine(
                self.inputLine.slice(0, self.cursorPosition - 1) +
                self.inputLine.slice(self.cursorPosition, self.inputLine.length));
            self.cursorPosition -= 1;
            self.positionInputCursor();
        }
    });
