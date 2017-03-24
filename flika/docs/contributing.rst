.. _contributing:


Contribution getting started
============================

Contributions are highly welcomed and appreciated.  Every little help counts,
so do not hesitate!

.. contents:: Contribution links
   :depth: 2


.. _submitfeedback:

Feature requests and feedback
-----------------------------

Do you like flika?  Share some love on Twitter or in your blog posts!

We'd also like to hear about your propositions and suggestions.  Feel free to
`submit them as issues <https://github.com/flika-org/flika/issues>`_ and:

* Explain in detail how they should work.
* Keep the scope as narrow as possible.  This will make it easier to implement.


.. _reportbugs:

Report bugs
-----------

Report bugs for flika in the `issue tracker <https://github.com/flika-org/flika/issues>`_.

If you are reporting a bug, please include:

* Your operating system name and version.
* Any details about your local setup that might be helpful in troubleshooting,
  specifically Python interpreter version,
  installed libraries and flika version.
* Detailed steps to reproduce the bug.

If you can write a demonstration script that currently doesn't work but should,
that is a very useful commit to make as well, even if you can't find how
to fix the bug yet.


.. _fixbugs:

Fix bugs
--------

Look through the GitHub issues for bugs.  Here is a filter you can use:
https://github.com/flika-org/flika/labels/bug

:ref:`Talk <contact>` to developers to find out how you can fix specific bugs.

Don't forget to check the issue trackers of your favourite plugins, too!

.. _writeplugins:

Implement features
------------------

Look through the GitHub issues for enhancements.  Here is a filter you can use:
https://github.com/flika-org/flika/labels/enhancement

:ref:`Talk <contact>` to developers to find out how you can implement specific
features.

Write documentation
-------------------

flika could always use more documentation.  What exactly is needed?

* More complementary documentation.  Have you perhaps found something unclear?
* Documentation translations.  We currently have only English.
* Docstrings.  There can never be too many of them.
* Blog posts, articles and such -- they're all very appreciated.

You can also edit documentation files directly in the GitHub web interface,
without using a local copy.  This can be convenient for small fixes.

.. note::
    Build the documentation locally inside ``flika/flika/docs`` with the following command:

    .. code:: bash

        $ make html

    The built documentation should be available in the ``flika/flika/docs/_build/``.

.. _submitplugin:

Submitting plugins to flika
--------------------------------

Anyone can write and share plugins for flika. Your plugin must conform to the 
specifications described in the 
`flika_plugin_template <https://github.com/flika-org/flika_plugin_template>`_.
Download the plugin template to your ~/.FLIKA/plugins directory and modify it. When you
start flika, it will be listed under plugins. 

The ``flika`` organization maintains a centralized list of popular plugins to be 
displayed in the plugin manager. If you want your plugin downloadable via the plugin 
manager, you can submit your plugin to the flika developers by creating an issue in 
the `issue tracker <https://github.com/flika-org/flika/issues>`_, using the 'plugin'
label, and including the location of your plugin. 


.. _`pull requests`:
.. _pull-requests:

Preparing Pull Requests on GitHub
---------------------------------

.. note::
  What is a "pull request"?  It informs project's core developers about the
  changes you want to review and merge.  Pull requests are stored on
  `GitHub servers <https://github.com/flika-org/flika/pulls>`_.
  Once you send a pull request, we can discuss its potential modifications and
  even add more commits to it later on.

There's an excellent tutorial on how Pull Requests work in the
`GitHub Help Center <https://help.github.com/articles/using-pull-requests/>`_,
but here is a simple overview:

#. Fork the
   `flika GitHub repository <https://github.com/flika-org/flika>`__.  It's
   fine to use ``flika`` as your fork repository name because it will live
   under your user.

#. Clone your fork locally using `git <https://git-scm.com/>`_ and create a branch::

    $ git clone git@github.com:YOUR_GITHUB_USERNAME/flika.git
    $ cd flika
    # now, to fix a bug create your own branch off "master":
    
        $ git checkout -b your-bugfix-branch-name master

    # or to instead add a feature create your own branch off "features":
    
        $ git checkout -b your-feature-branch-name features

   Given we have "major.minor.micro" version numbers, bugfixes will usually 
   be released in micro releases whereas features will be released in 
   minor releases and incompatible changes in major releases.

   If you need some help with Git, follow this quick start
   guide: https://git.wiki.kernel.org/index.php/QuickStart

#. You can now edit your local working copy.

   You can now make the changes you want and run the tests as necessary.

#. Commit and push once your tests pass and you are happy with your change(s)::

    $ git commit -a -m "<commit message>"
    $ git push -u

   Make sure you add a message to ``CHANGELOG.rst`` and add yourself to
   ``AUTHORS``.  If you are unsure about either of these steps, submit your
   pull request and we'll help you fix it up.

#. Finally, submit a pull request through the GitHub website using this data::

    head-fork: YOUR_GITHUB_USERNAME/flika
    compare: your-branch-name

    base-fork: flika-org/flika
    base: master          # if it's a bugfix
    base: features        # if it's a feature


