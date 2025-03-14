import pytest
import pathlib
from flika.app.plugin_utils import PluginInfo, parse_plugin_info_xml
import packaging.version
from xml.etree import ElementTree


def test_plugin_info_from_xml_str():
    """Test the PluginInfo.from_xml_str method with a sample XML string."""
    # Sample XML string representing a plugin configuration
    xml_str = """
    <plugin name="Detect Puffs">
        <directory>
            detect_puffs
        </directory>
        <version>
            2024.03.11
        </version>
        <author>
            Kyle Ellefsen
        </author>
        <url>
            https://github.com/kyleellefsen/detect_puffs/archive/master.zip
        </url>
        <dependencies>
            <dependency name='skimage'></dependency>
            <dependency name='matplotlib'></dependency>
            <dependency name='PyOpenGL'></dependency>
            <dependency name='openpyxl'></dependency>
        </dependencies>
        <menu_layout>
            <action location="threshold_cluster" function="threshold_cluster.gui">Threshold Cluster</action>
            <action location="puff_simulator.puff_simulator" function="simulate_puffs.gui">Simulate Puffs</action>
            <action location="threshold_cluster" function="load_flika_file_gui">Load .flika file</action>
            <action location="threshold_cluster" function="run_demo">Run Demo</action>
            <action location="threshold_cluster" function="launch_docs">Docs</action>
        </menu_layout>
    </plugin>
    """
    
    # Now we expect the method to work and not raise NotImplementedError
    plugin_info = PluginInfo.from_xml_str(xml_str)
    
    # Verify the basic attributes
    assert plugin_info.name == "Detect Puffs"
    assert plugin_info.directory == "detect_puffs"
    assert isinstance(plugin_info.version, packaging.version.Version)
    assert plugin_info.version == packaging.version.Version("2024.03.11")
    assert plugin_info.author == "Kyle Ellefsen"
    assert plugin_info.url == "https://github.com/kyleellefsen/detect_puffs/archive/master.zip"
    
    # Check dependencies
    assert isinstance(plugin_info.dependencies, list)
    assert len(plugin_info.dependencies) == 4
    assert "skimage" in plugin_info.dependencies
    assert "matplotlib" in plugin_info.dependencies
    assert "PyOpenGL" in plugin_info.dependencies
    assert "openpyxl" in plugin_info.dependencies
    
    # Check menu_layout
    assert isinstance(plugin_info.menu_layout, list)
    assert len(plugin_info.menu_layout) == 5


def test_plugin_info_incomplete_xml():
    """Test that from_xml_str handles incomplete XML gracefully."""
    incomplete_xml = "<plugin name='Test'></plugin>"
    
    # This should still work with minimal information
    plugin_info = PluginInfo.from_xml_str(incomplete_xml)
    
    # Verify default values are used when not provided
    assert plugin_info.name == "Test"
    assert plugin_info.directory == ""
    assert isinstance(plugin_info.version, packaging.version.Version)
    assert plugin_info.version == packaging.version.Version("0.0.0")
    assert plugin_info.dependencies == []
    assert plugin_info.menu_layout == []
    assert plugin_info.author == ""
    assert plugin_info.url == ""


def test_plugin_info_malformed_xml():
    """Test that from_xml_str handles malformed XML gracefully."""
    malformed_xml = "<plugin name='Test'><unclosed_tag>"
    
    # With the implemented method, it should raise an XML parsing error
    with pytest.raises(ElementTree.ParseError):
        plugin_info = PluginInfo.from_xml_str(malformed_xml) 