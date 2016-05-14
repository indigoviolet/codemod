modone
=======

Overview
--------

This is a fork of [Facebook's codemod library](https://github.com/facebook/codemod), simplified to operate on only
one path at a time. All file-system traversal and filtering code has been
ripped out.

This is for simplicity, so that you can use more powerful tools like `find` and
`grep` to actually identify the files you want to codemod, leaving the actual
work of doing replacements (and prompting you) to this tool.

For example

```
    grep -E -l '\$(\.|\()' -R . | xargs grep -L 'jquery'

```

returns all filenames under this root that use the jquery library but don't
mention the word `jquery` -- indicating they might not have imported it for
some reason.

Here's how we might then fix them:

```
grep -E -l '\$(\.|\()' -R . | xargs grep -L 'jquery' | xargs -o -IARG modone -m --path ARG --default-no '^(var.*?require.*?)\n'  '\1\nvar $ = require("jquery");\n'

```

Note
----

In many ways I've just removed functionality from codemod; the one thing I've
added (as of May 2016) is the ability to accept and operate on a single
`--path`. This is a powerful change because it opens the doors to using other
tools to expand codemod's behavior.

I initially went the route of adding more options to codemod, like a
`--path_regexp`, `--exclude-contents-regexp` etc and realized that this was
unnecessary.

I've released this stripped-down code as a separate library because I imagine
that the codemod folks don't want to force their users to go this route or
break their scripts.

Dependencies
------------

* python2

Credits
-------

[Facebook's codemod library](https://github.com/facebook/codemod),

Licensed under the Apache License, Version 2.0.
