.. _plugins:
.. _`writing_plugins`:

Writing plugins
===============

It is easy to extend flika by making your own plugin. To start, download
the `plugin template <https://github.com/flika-org/flika_plugin_template>`_
and put it into your ~/.FLIKA/plugins directory. (The ~ stands for your 
home directory. On Windows this is usually ``C:\Users\myname``, where ``myname``
is your username.) 

The directory containing your plugin must contain the following files

- ``__init__.py`` - Plugins are python modules and have to be imported. This can be empty
- ``about.html`` - The html in this file will be displayed by flika's plugin manager.
- ``info.xml`` - This specifies plugin metadata that flika's plugin manager will use and display.
    
The ``info.xml`` file should look something like this

.. code-block:: xml

  <plugin name='flika plugin template'>
    <directory>
      flika_plugin_template
    </directory>

    <version>
      2017.03.21
    </version>

    <author>
      Author Name
    </author>

    <url>
      https://github.com/flika-org/flika_plugin_template/archive/master.zip
    </url>

    <dependencies>
      <dependency name='dependency_name_1'></dependency>
      <dependency name='dependency_name_2'></dependency>
    </dependencies>

    <menu_layout>
      <action location='file_or_submodule_containing_function1' function='function1_name'>Function 1</action>
      <action location='file_or_submodule_containing_function2' function='function2_name'>Function 2</action>
    </menu_layout>

  </plugin>


The ``<menu_layout>`` is where you specify where in your plugin flika should for the functions that can be run by users.


Sample Plugins
===============

- `Sample plugin 1 <https://github.com/flika-org/sample_plugin_1>`_
- More coming soon.

If you'd like to contribute a sample plugin, please :ref:`contact us<contact>`. 


Submitting Plugins
==================

If you would like to submit your plugin to be displayed in the Plugin Manager, follow the instructions at :ref:`submitplugin`.







