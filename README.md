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
grep -E -l '\$(\.|\()' -R . | xargs grep -L 'jquery' | xargs -o -IARG codemod -m --path ARG --default-no '^(var.*?require.*?)\n'  '\1\nvar $ = require("jquery");\n'

```


Install
-------


Usage
-----

The last two arguments are a regular expression to match and a substitution string, respectively.  Or you can omit the substitution string, and just be prompted on each match for whether you want to edit in your editor.


Dependencies
------------

* python2

Credits
-------

Licensed under the Apache License, Version 2.0.
