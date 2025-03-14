import sys
from qtpy import QtCore, QtGui

def format(color, style=''):
    """Return a QtGui.QTextCharFormat with the given attributes.
    """
    _color = QtGui.QColor(color)

    _format = QtGui.QTextCharFormat()
    _format.setForeground(_color)
    if 'bold' in style:
        _format.setFontWeight(QtGui.QFont.Weight.Bold if hasattr(QtGui.QFont, 'Weight') else QtGui.QFont.Bold)
    if 'italic' in style:
        _format.setFontItalic(True)
    return _format


# Syntax styles that can be shared by all languages
STYLES = {
    'keyword': format('blue'),
    'operator': format('red'),
    'brace': format('black'),
    'defclass': format('black', 'bold'),
    'string': format('magenta'),
    'string2': format('darkMagenta'),
    'comment': format('darkGreen', 'italic'),
    'self': format('black', 'italic'),
    'numbers': format('brown'),
}


class PythonHighlighter (QtGui.QSyntaxHighlighter):
    """Syntax highlighter for the Python language.
    """
    # Python keywords
    keywords = [
        'and', 'assert', 'break', 'class', 'continue', 'def',
        'del', 'elif', 'else', 'except', 'exec', 'finally',
        'for', 'from', 'global', 'if', 'import', 'in',
        'is', 'lambda', 'not', 'or', 'pass', 'print',
        'raise', 'return', 'try', 'while', 'yield',
        'None', 'True', 'False',
    ]

    # Python operators
    operators = [
        '=',
        # Comparison
        '==', '!=', '<', '<=', '>', '>=',
        # Arithmetic
        r'\+', '-', r'\*', '/', '//', r'%', r'\*\*',
        # In-place
        r'\+=', '-=', r'\*=', '/=', r'%=',
        # Bitwise
        r'\^', r'\|', r'\&', r'\~', '>>', '<<',
    ]

    # Python braces
    braces = [
        r'\{', r'\}', r'\(', r'\)', r'\[', r'\]',
    ]
    
    def __init__(self, document):
        QtGui.QSyntaxHighlighter.__init__(self, document)

        # Multi-line strings (expression, flag, style)
        # Use QRegExp if QRegularExpression is not available
        if hasattr(QtCore, 'QRegularExpression'):
            self.tri_single = (QtCore.QRegularExpression("'''"), 1, STYLES['string2'])
            self.tri_double = (QtCore.QRegularExpression('"""'), 2, STYLES['string2'])
            self.RegexClass = QtCore.QRegularExpression
        else:
            self.tri_single = (QtCore.QRegExp("'''"), 1, STYLES['string2'])
            self.tri_double = (QtCore.QRegExp('"""'), 2, STYLES['string2'])
            self.RegexClass = QtCore.QRegExp

        rules = []

        # Keyword, operator, and brace rules
        rules += [(r'\b%s\b' % w, 0, STYLES['keyword'])
            for w in PythonHighlighter.keywords]
        rules += [(r'%s' % o, 0, STYLES['operator'])
            for o in PythonHighlighter.operators]
        rules += [(r'%s' % b, 0, STYLES['brace'])
            for b in PythonHighlighter.braces]

        # All other rules
        rules += [
            # 'self'
            (r'\bself\b', 0, STYLES['self']),

            # Double-quoted string, possibly containing escape sequences
            (r'"[^"\\]*(\\.[^"\\]*)*"', 0, STYLES['string']),
            # Single-quoted string, possibly containing escape sequences
            (r"'[^'\\]*(\\.[^'\\]*)*'", 0, STYLES['string']),

            # 'def' followed by an identifier
            (r'\bdef\b\s*(\w+)', 1, STYLES['defclass']),
            # 'class' followed by an identifier
            (r'\bclass\b\s*(\w+)', 1, STYLES['defclass']),

            # From '#' until a newline
            (r'#[^\n]*', 0, STYLES['comment']),

            # Numeric literals
            (r'\b[+-]?[0-9]+[lL]?\b', 0, STYLES['numbers']),
            (r'\b[+-]?0[xX][0-9A-Fa-f]+[lL]?\b', 0, STYLES['numbers']),
            (r'\b[+-]?[0-9]+(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?\b', 0, STYLES['numbers']),
        ]

        # Build a RegExp for each pattern
        self.rules = [(self.RegexClass(pat), index, fmt)
            for (pat, index, fmt) in rules]


    def highlightBlock(self, text):
        """Apply syntax highlighting to the given block of text.
        """
        # Do other syntax formatting
        for expression, nth, format in self.rules:
            if hasattr(QtCore, 'QRegularExpression'):
                # For QRegularExpression
                match = expression.match(text, 0)
                while match.hasMatch():
                    index = match.capturedStart()
                    length = match.capturedLength()
                    if nth > 0:
                        index = match.capturedStart(nth)
                        length = match.capturedLength(nth)
                    self.setFormat(index, length, format)
                    match = expression.match(text, index + length)
            else:
                # For QRegExp
                index = expression.indexIn(text)
                while index >= 0:
                    length = expression.matchedLength()
                    if nth > 0:
                        index = expression.pos(nth)
                        length = len(expression.cap(nth))
                    self.setFormat(index, length, format)
                    index = expression.indexIn(text, index + length)

        self.setCurrentBlockState(0)

        # Do multi-line strings
        in_multiline = self.match_multiline(text, *self.tri_single)
        if not in_multiline:
            in_multiline = self.match_multiline(text, *self.tri_double)


    def match_multiline(self, text, delimiter, in_state, style):
        """Do highlighting of multi-line strings. ``delimiter`` should be a
        ``QRegExp`` or ``QRegularExpression`` for triple-single-quotes or triple-double-quotes, and
        ``in_state`` should be a unique integer to represent the corresponding
        state changes when inside those strings. Returns True if we're still
        inside a multi-line string when this function is finished.
        """
        # If inside triple-single quotes, start at 0
        if self.previousBlockState() == in_state:
            start = 0
            add = 0
        # Otherwise, look for the delimiter on this line
        else:
            if hasattr(QtCore, 'QRegularExpression'):
                # For QRegularExpression
                match = delimiter.match(text)
                start = match.capturedStart() if match.hasMatch() else -1
                add = match.capturedLength() if match.hasMatch() else 0
            else:
                # For QRegExp
                start = delimiter.indexIn(text)
                add = delimiter.matchedLength()

        # As long as there's a delimiter match on this line...
        while start >= 0:
            # Look for the ending delimiter
            if hasattr(QtCore, 'QRegularExpression'):
                # For QRegularExpression
                match = delimiter.match(text, start + add)
                end = match.capturedStart() if match.hasMatch() else -1
            else:
                # For QRegExp
                end = delimiter.indexIn(text, start + add)
                
            # Ending delimiter on this line?
            if end >= add:
                # Fix the conditional to properly handle match objects
                if hasattr(QtCore, 'QRegularExpression') and match.hasMatch():
                    length = end - start + add + match.capturedLength()
                else:
                    length = end - start + add + delimiter.matchedLength()
                self.setCurrentBlockState(0)
            # No; multi-line string
            else:
                self.setCurrentBlockState(in_state)
                length = len(text) - start + add
            # Apply formatting
            self.setFormat(start, length, style)
            # Look for the next match
            if hasattr(QtCore, 'QRegularExpression'):
                # For QRegularExpression
                match = delimiter.match(text, start + length)
                start = match.capturedStart() if match.hasMatch() else -1
            else:
                # For QRegExp
                start = delimiter.indexIn(text, start + length)

        # Return True if still inside a multi-line string, False otherwise
        if self.currentBlockState() == in_state:
            return True
        else:
            return False