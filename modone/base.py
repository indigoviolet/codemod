#!/usr/bin/env python2

# Copyright (c) 2007-2008 Facebook
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# See accompanying file LICENSE.
#


import argparse
import os
import re
import sys
import textwrap
from math import ceil

def run_interactive(query, editor=None, just_count=False, default_no=False):
    """
    Asks the user about each patch suggested by the result of the query.

    @param query        An instance of the Query class.
    @param editor       Name of editor to use for manual intervention, e.g.
                        'vim'
                        or 'emacs'.  If omitted/None, defaults to $EDITOR
                        environment variable.
    @param just_count   If true: don't run normally.  Just print out number of
                        places in the codebase where the query matches.
    """

    global yes_to_all  # noqa

    # Okay, enough of this foolishness of computing start and end.
    # Let's ask the user about some one line diffs!
    print 'Searching for first instance...'
    suggestions = query.generate_patches()

    if just_count:
        for count, _ in enumerate(suggestions):
            terminal_move_to_beginning_of_line()
            print count,
            sys.stdout.flush()  # since print statement ends in comma
        print
        return

    for patch in suggestions:
        _ask_about_patch(patch, editor, default_no)
        print 'Searching...'


def line_transformation_suggestor(line_transformation, line_filter=None):
    """
    Returns a suggestor (a function that takes a list of lines and yields
    patches) where suggestions are the result of line-by-line transformations.

    @param line_transformation  Function that, given a line, returns another
                                line
                                with which to replace the given one.  If the
                                output line is different from the input line,
                                the
                                user will be prompted about whether to make the
                                change.  If the output is None, this means "I
                                don't have a suggestion, but the user should
                                still be asked if zhe wants to edit the line."
    @param line_filter          Given a line, returns True or False.  If False,
                                a line is ignored (as if line_transformation
                                returned the line itself for that line).
    """
    def suggestor(lines):
        for line_number, line in enumerate(lines):
            if line_filter and not line_filter(line):
                continue
            candidate = line_transformation(line)
            if candidate is None:
                yield Patch(line_number)
            else:
                yield Patch(line_number, new_lines=[candidate])
    return suggestor


def regex_suggestor(regex, substitution=None, ignore_case=False,
                    line_filter=None):
    if isinstance(regex, str):
        if ignore_case is False:
            regex = re.compile(regex)
        else:
            regex = re.compile(regex, re.IGNORECASE)

    if substitution is None:
        line_transformation = lambda line: None if regex.search(line) else line
    else:
        line_transformation = lambda line: regex.sub(substitution, line)
    return line_transformation_suggestor(line_transformation, line_filter)


def multiline_regex_suggestor(regex, substitution=None, ignore_case=False):
    """
    Return a suggestor function which, given a list of lines, generates patches
    to substitute matches of the given regex with (if provided) the given
    substitution.

    @param regex         Either a regex object or a string describing a regex.
    @param substitution  Either None (meaning that we should flag the matches
                         without suggesting an alternative), or a string (using
                         \1 notation to backreference match groups) or a
                         function (that takes a match object as input).
    """
    if isinstance(regex, str):
        if ignore_case is False:
            regex = re.compile(regex, re.DOTALL)
        else:
            regex = re.compile(regex, re.DOTALL | re.IGNORECASE)

    if isinstance(substitution, str):
        substitution_func = lambda match: match.expand(substitution)
    else:
        substitution_func = substitution

    def suggestor(lines):
        pos = 0
        while True:
            match = regex.search(''.join(lines), pos)
            if not match:
                break
            start_row, start_col = _index_to_row_col(lines, match.start())
            end_row, end_col = _index_to_row_col(lines, match.end() - 1)

            if substitution is None:
                new_lines = None
            else:
                # TODO: ugh, this is hacky.  Clearly I need to rewrite
                # this to use
                # character-level patches, rather than line-level patches.
                new_lines = substitution_func(match)
                if new_lines is not None:
                    new_lines = ''.join((
                        lines[start_row][:start_col],
                        new_lines,
                        lines[end_row][end_col + 1:]
                    ))

            yield Patch(
                start_line_number=start_row,
                end_line_number=end_row + 1,
                new_lines=new_lines
            )
            pos = match.start() + 1

    return suggestor


def _index_to_row_col(lines, index):
    r"""
    >>> lines = ['hello\n', 'world\n']
    >>> _index_to_row_col(lines, 0)
    (0, 0)
    >>> _index_to_row_col(lines, 7)
    (1, 1)
    """
    if index < 0:
        raise IndexError('negative index')
    current_index = 0
    for line_number, line in enumerate(lines):
        line_length = len(line)
        if current_index + line_length > index:
            return line_number, index - current_index
        current_index += line_length
    raise IndexError('index %d out of range' % index)


class Query(object):
    """
    Represents a suggestor, along with a set of constraints on which files
    should be fed to that suggestor.

    """

    def __init__(self, suggestor, path):

        """
        @param suggestor            A function that takes a list of lines and
                                    generates instances of Patch to suggest.
                                    (Patches should not specify paths.)

        """
        self.suggestor = suggestor
        self.path = path

    def generate_patches(self):
        """
        Generates a list of patches for file
        that satisfy the given conditions given
        query conditions, where patches for
        each file are suggested by self.suggestor.
        """

        for path in [self.path]:
            try:
                lines = list(open(path))
            except IOError:
                # If we can't open the file--perhaps it's a symlink whose
                # destination no loner exists--then short-circuit.
                continue

            for patch in self.suggestor(lines):
                old_lines = lines[
                    patch.start_line_number:patch.end_line_number]
                if patch.new_lines is None or patch.new_lines != old_lines:
                    patch.path = path
                    yield patch
                    # re-open file, in case contents changed
                    lines[:] = list(open(path))

    def run_interactive(self, **kargs):
        run_interactive(self, **kargs)




class Patch(object):
    """
    Represents a range of a file and (optionally) a list of lines with which to
    replace that range.

    >>> p = Patch(2, 4, ['X', 'Y', 'Z'], 'x.php')
    >>> print p.render_range()
    x.php:2-3
    >>> l = ['a', 'b', 'c', 'd', 'e', 'f']
    >>> p.apply_to(l)
    >>> l
    ['a', 'b', 'X', 'Y', 'Z', 'e', 'f']
    """

    def __init__(self, start_line_number, end_line_number=None, new_lines=None,
                 path=None):  # noqa
        """
        Constructs a Patch object.

        @param end_line_number  The line number just *after* the end of
                                the range.
                                Defaults to
                                start_line_number + 1, i.e. a one-line
                                diff.
        @param new_lines        The set of lines with which to
                                replace the range
                                specified, or a newline-delimited string.
                                Omitting this means that
                                this "patch" doesn't actually
                                suggest a change.
        @param path             Path is optional only so that
                                suggestors that have
                                been passed a list of lines
                                don't have to set the
                                path explicitly.
                                (It'll get set by the suggestor's caller.)
        """
        self.path = path
        self.start_line_number = start_line_number
        self.end_line_number = end_line_number
        self.new_lines = new_lines

        if self.end_line_number is None:
            self.end_line_number = self.start_line_number + 1
        if isinstance(self.new_lines, str):
            self.new_lines = self.new_lines.splitlines(True)

    def __repr__(self):
        return 'Patch()' % ', '.join(map(repr, [
            self.path,
            self.start_line_number,
            self.end_line_number,
            self.new_lines
        ]))

    def apply_to(self, lines):
        if self.new_lines is None:
            raise ValueError('Can\'t apply patch without suggested new lines.')
        lines[self.start_line_number:self.end_line_number] = self.new_lines

    def render_range(self):
        path = self.path or '<unknown>'
        if self.start_line_number == self.end_line_number - 1:
            return '%s:%d' % (path, self.start_line_number)
        else:
            return '%s:%d-%d' % (
                path,
                self.start_line_number, self.end_line_number - 1
            )


def print_patch(patch, lines_to_print, file_lines=None):
    if file_lines is None:
        file_lines = list(open(patch.path))

    size_of_old = patch.end_line_number - patch.start_line_number
    size_of_new = len(patch.new_lines) if patch.new_lines else 0
    size_of_diff = size_of_old + size_of_new
    size_of_context = max(0, lines_to_print - size_of_diff)
    size_of_up_context = int(size_of_context / 2)
    size_of_down_context = int(ceil(size_of_context / 2))
    start_context_line_number = patch.start_line_number - size_of_up_context
    end_context_line_number = patch.end_line_number + size_of_down_context

    def print_file_line(line_number):  # noqa
        # Why line_number is passed here?
        print ('  %s' % file_lines[i]) if (
            0 <= i < len(file_lines)) else '~\n',

    for i in xrange(start_context_line_number, patch.start_line_number):
        print_file_line(i)
    for i in xrange(patch.start_line_number, patch.end_line_number):
        if patch.new_lines is not None:
            terminal_print('- %s' % file_lines[i], color='RED')
        else:
            terminal_print('* %s' % file_lines[i], color='YELLOW')
    if patch.new_lines is not None:
        for line in patch.new_lines:
            terminal_print('+ %s' % line, color='GREEN')
    for i in xrange(patch.end_line_number, end_context_line_number):
        print_file_line(i)

yes_to_all = False


def _ask_about_patch(patch, editor, default_no):
    global yes_to_all
    default_action = 'n' if default_no else 'y'
    terminal_clear()
    terminal_print('%s\n' % patch.render_range(), color='WHITE')
    print

    lines = list(open(patch.path))
    print_patch(patch, terminal_get_size()[0] - 20, lines)

    print

    if patch.new_lines is not None:
        if not yes_to_all:
            if default_no:
                print ('Accept change (y = yes, n = no [default], e = edit, ' +
                       'A = yes to all, E = yes+edit)? '),
            else:
                print ('Accept change (y = yes [default], n = no, e = edit, ' +
                       'A = yes to all, E = yes+edit)? '),
            p = _prompt('yneEA', default=default_action)
        else:
            p = 'y'
    else:
        print '(e = edit [default], n = skip line)? ',
        p = _prompt('en', default='e')

    if p in 'A':
        yes_to_all = True
        p = 'y'
    if p in 'yE':
        patch.apply_to(lines)
        _save(patch.path, lines)
    if p in 'eE':
        run_editor(patch.start_position, editor)


def _prompt(letters='yn', default=None):
    """
    Wait for the user to type a character (and hit Enter).  If the user enters
    one of the characters in `letters`, return that character.  If the user
    hits Enter without entering a character, and `default` is specified,
    returns `default`.  Otherwise, asks the user to enter a character again.
    """
    while True:
        try:
            input_text = sys.stdin.readline().strip()
        except KeyboardInterrupt:
            sys.exit(0)
        if input_text and input_text in letters:
            return input_text
        if default is not None and input_text == '':
            return default
        print 'Come again?'


def _save(path, lines):
    file_w = open(path, 'w')
    for line in lines:
        file_w.write(line)
    file_w.close()


def run_editor(position, editor=None):
    editor = editor or os.environ.get('EDITOR') or 'vim'
    os.system('%s +%d %s' % (editor, position.line_number + 1, position.path))


#
# Functions for working with the terminal.  Should probably be moved to a
# standalone library.
#

def terminal_get_size(default_size=(25, 80)):
    """
    Return (number of rows, number of columns) for the terminal,
    if they can be determined, or `default_size` if they can't.
    """

    def ioctl_gwinsz(fd):  # TABULATION FUNCTIONS
        try:  # Discover terminal width
            import fcntl
            import termios
            import struct
            return struct.unpack(
                'hh', fcntl.ioctl(fd, termios.TIOCGWINSZ, '1234')
            )
        except Exception:
            return None

    # try open fds
    size = ioctl_gwinsz(0) or ioctl_gwinsz(1) or ioctl_gwinsz(2)
    if not size:
        # ...then ctty
        try:
            fd = os.open(os.ctermid(), os.O_RDONLY)
            size = ioctl_gwinsz(fd)
            os.close(fd)
        except Exception:
            pass
    if not size:
        # env vars or finally defaults
        try:
            size = (os.environ.get('LINES'), os.environ.get('COLUMNS'))
        except Exception:
            return default_size

    return map(int, size)


def terminal_clear():
    """
    Like calling the `clear` UNIX command.  If that fails, just prints a bunch
    of newlines :-P
    """
    if not _terminal_use_capability('clear'):
        print '\n' * 8


def terminal_move_to_beginning_of_line():
    """
    Jumps the cursor back to the beginning of the current line of text.
    """
    if not _terminal_use_capability('cr'):
        print


def _terminal_use_capability(capability_name):
    """
    If the terminal supports the given capability, output it.  Return whether
    it was output.
    """
    import curses
    curses.setupterm()
    capability = curses.tigetstr(capability_name)
    if capability:
        sys.stdout.write(capability)
    return bool(capability)


def terminal_print(text, color):
    """Print text in the specified color, without a terminating newline."""
    _terminal_set_color(color)
    print text,
    _terminal_restore_color()


def _terminal_set_color(color):
    import curses

    def color_code(set_capability, possible_colors):
        try:
            color_index = possible_colors.split(' ').index(color)
        except ValueError:
            return None
        set_code = curses.tigetstr(set_capability)
        if not set_code:
            return None
        return curses.tparm(set_code, color_index)
    code = (
        color_code(
            'setaf', 'BLACK RED GREEN YELLOW BLUE MAGENTA CYAN WHITE'
        ) or color_code(
            'setf', 'BLACK BLUE GREEN CYAN RED MAGENTA YELLOW WHITE'
        )
    )
    if code:
        sys.stdout.write(code)


def _terminal_restore_color():
    import curses
    sys.stdout.write(curses.tigetstr('sgr0'))

#
# Code to make this run as an executable from the command line.
#


def _parse_command_line():
    global yes_to_all

    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=textwrap.dedent(r"""

            modone is a tool/library to assist you with large-scale codebase
            refactors that can be partially automated but still require human
            oversight and occassional intervention.

            Example: Let's say you're deprecating your use
            of the <font> tag.  From the
            command line, you might make progress by running:

            grep -l '<font>' | xargs -o -IARG modone -m --path ARG \
                         '<font *color="?(.*?)"?>(.*?)</font>' \
                         '<span style="color: \1;">\2</span>'

            For each match of the regex, you'll be shown a colored diff, and
            asked if you want to accept the change (the replacement of the
            <font> tag with a <span> tag), reject it, or edit the line in
            question in your $EDITOR of choice.
        """),
        epilog=textwrap.dedent(r"""
        You can also use modone for transformations that are much more
        sophisticated than regular expression substitution.  Rather than
        using the command line, you write Python code that looks like:

              import modone
              modone.Query(...).run_interactive()

            See the documentation for the Query class for details.
            """)
    )

    parser.add_argument('-m', action='store_true',
                        help='Have regex work over multiple lines '
                             '(e.g. have dot match newlines). '
                             'By default, modone applies the regex one '
                             'line at a time.')
    parser.add_argument('-i', action='store_true',
                        help='Perform case-insensitive search.')

    parser.add_argument('--path', action='store', type=str)

    parser.add_argument('--accept-all', action='store_true',
                        help='Automatically accept all '
                             'changes (use with caution).')

    parser.add_argument('--default-no', action='store_true',
                        help='If set, this will make the default '
                             'option to not accept the change.')

    parser.add_argument('--editor', action='store', type=str,
                        help='Specify an editor, e.g. "vim" or emacs". '
                        'If omitted, defaults to $EDITOR environment '
                        'variable.')
    parser.add_argument('--count', action='store_true',
                        help='Don\'t run normally.  Instead, just print '
                             'out number of times places in the codebase '
                             'where the \'query\' matches.')
    parser.add_argument('--test', action='store_true',
                        help='Don\'t run normally.  Instead, just run '
                             'the unit tests embedded in the modone library.')

    parser.add_argument('match', nargs='?', action='store', type=str,
                        help='Regular expression to match.')
    parser.add_argument('subst', nargs='?', action='store', type=str,
                        help='Substitution to replace with.')

    arguments = parser.parse_args()

    if arguments.test:
        import doctest
        doctest.testmod(verbose=True)
        sys.exit(0)

    if arguments.path is None:
        parser.print_usage()
        sys.exit(0)

    yes_to_all = arguments.accept_all

    query_options = {}

    query_options['suggestor'] = (
        multiline_regex_suggestor if arguments.m else regex_suggestor
    )(arguments.match, arguments.subst, arguments.i)
    query_options['path'] = arguments.path

    options = {}
    options['query'] = Query(**query_options)
    if arguments.editor is not None:
        options['editor'] = arguments.editor
    options['just_count'] = arguments.count
    options['default_no'] = arguments.default_no

    return options


def main():
    options = _parse_command_line()
    run_interactive(**options)

if __name__ == '__main__':
    main()
