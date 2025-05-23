"""
This module contains utility functions for plugins.

Importantly, it contains the list of plugins that show up in Flika, and the
PluginInfo class, which stores plugin metadata.
"""

import dataclasses
import glob
import pathlib
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ElementTree

import packaging.version

plugin_info_urls_by_name = {
    "Beam Splitter": "https://raw.githubusercontent.com/BrettJSettle/BeamSplitter/master/",
    "Detect Puffs": "https://raw.githubusercontent.com/kyleellefsen/detect_puffs/master/",
    "Global Analysis": "https://raw.githubusercontent.com/BrettJSettle/GlobalAnalysisPlugin/master/",
    "Pynsight": "http://raw.githubusercontent.com/kyleellefsen/pynsight/master/",
    "QuantiMus": "http://raw.githubusercontent.com/Quantimus/quantimus/master/",
    "Rodent Tracker": "https://raw.githubusercontent.com/kyleellefsen/rodentTracker/master/",
}


def get_plugin_directory() -> pathlib.Path:
    """
    Get the plugin directory path, creating it if it doesn't exist.

    Returns:
        pathlib.Path: The path to the plugin directory.
    """
    local_flika_directory = pathlib.Path.home() / ".FLIKA"
    plugin_directory = local_flika_directory / "plugins"

    # Create plugin directory if it doesn't exist
    plugin_directory.mkdir(parents=True, exist_ok=True)

    # Create empty __init__.py file if it doesn't exist
    init_file = plugin_directory / "__init__.py"
    if not init_file.exists():
        init_file.touch()

    # Add to sys.path if not already present
    for directory in (str(local_flika_directory), str(plugin_directory)):
        if directory not in sys.path:
            sys.path.insert(0, directory)

    return plugin_directory


def _get_path_to_plugin(directory: str) -> pathlib.Path:
    """A simple map from the plugin directory name to the full path."""
    return get_plugin_directory() / directory


def get_local_plugin_list() -> list[str]:
    """Returns the (directory) names of all local plugins"""
    paths: list[str] = []
    for path_str in glob.glob(str(get_plugin_directory() / "*")):
        path = pathlib.Path(path_str)
        if path.is_dir() and path.joinpath("info.xml").exists():
            paths.append(path.name)
    return paths


def get_plugin_info_xml_from_url(info_url: str) -> str | urllib.error.HTTPError:
    info_url_xml: str = urllib.parse.urljoin(info_url, "info.xml")
    try:
        info_xml_bytes: bytes = urllib.request.urlopen(info_url_xml).read()
        info_xml_str: str = info_xml_bytes.decode("utf-8")
    except urllib.error.HTTPError as e:
        return e
    return info_xml_str


def parse_plugin_info_xml(xml_str: str) -> dict:
    """
    Parse an XML string into a dictionary.
    """
    tree = ElementTree.fromstring(xml_str)

    def step(item: ElementTree.Element) -> dict:
        d = {}
        if item.text and item.text.strip():
            d["#text"] = item.text.strip()
        for k, v in item.items():
            d[f"@{k}"] = v
        for k in list(item):
            if k.tag not in d:
                d[k.tag] = step(k)
            elif isinstance(d[k.tag], list):
                d[k.tag].append(step(k))
            else:
                d[k.tag] = [d[k.tag], step(k)]
        if len(d) == 1 and "#text" in d:
            return d["#text"]
        return d

    return step(tree)


@dataclasses.dataclass(frozen=True)
class PluginInfo:
    author: str  # The author of the plugin
    dependencies: list[str]  # The dependencies of the plugin
    description: str  # The description of the plugin
    directory: str  # The name of the module to import. This will be changed to 'module_name' eventually.
    documentation_url: str  # The url of the documentation of the plugin
    path_to_plugin: pathlib.Path  # The full path to the plugin directory
    info_url: str  # The URL of the plugin info
    last_modified: float  # The last modified date of the plugin
    latest_version: packaging.version.Version  # The latest version of the plugin
    menu_layout: list[dict]  # The menu layout of the plugin
    name: str  # The human-readable name of the plugin
    url: str  # The URL of the plugin
    version: packaging.version.Version  # The version of the plugin

    @classmethod
    def from_xml_str(cls, xml_str: str) -> "PluginInfo":
        """
        Create a PluginInfo object from an XML string.

        Args:
            xml_str: The XML string to parse.

        Returns:
            A PluginInfo object.

        Raises:
            ElementTree.ParseError: If the XML string cannot be parsed.
        """
        # Parse the XML string into a dictionary
        try:
            plugin_dict = parse_plugin_info_xml(xml_str)
        except ElementTree.ParseError as e:
            raise e

        # Extract plugin name from the 'name' attribute
        name = plugin_dict.get("@name", "")

        # Extract other required fields, stripping whitespace
        directory = plugin_dict.get("directory", "").strip()
        path_to_plugin = (
            _get_path_to_plugin(directory) if directory else pathlib.Path(".")
        )
        version_str = plugin_dict.get("version", "0.0.0").strip()
        author = plugin_dict.get("author", "").strip()
        url = plugin_dict.get("url", "").strip()

        # Parse dependencies - If dependencies is a dict with dependency elements
        dependencies_list = []
        dependencies = plugin_dict.get("dependencies", {})
        if isinstance(dependencies, dict):
            # When there's a single dependency, it will be a dict
            if "dependency" in dependencies:
                dependency = dependencies["dependency"]
                if isinstance(dependency, dict) and "@name" in dependency:
                    dependencies_list.append(dependency["@name"])
                elif isinstance(dependency, list):
                    # Multiple dependencies as a list
                    for dep in dependency:
                        if isinstance(dep, dict) and "@name" in dep:
                            dependencies_list.append(dep["@name"])

        # Parse menu_layout - actions with their properties
        menu_layout_list = []
        menu_layout = plugin_dict.get("menu_layout", {})
        if isinstance(menu_layout, dict) and "action" in menu_layout:
            actions = menu_layout["action"]
            if isinstance(actions, dict):
                # Single action
                menu_layout_list.append(actions)
            elif isinstance(actions, list):
                # Multiple actions
                menu_layout_list.extend(actions)

        # Providing default values for required fields not in the XML
        description = plugin_dict.get("description", "")
        documentation_url = plugin_dict.get(
            "documentation_url", "/".join(url.split("/")[:-2])
        )
        info_url = plugin_dict.get("info_url", "")
        last_modified = float(plugin_dict.get("last_modified", 0))
        latest_version = packaging.version.Version(
            plugin_dict.get("latest_version", version_str)
        )

        # Create and return the PluginInfo object
        return cls(
            author=author,
            dependencies=dependencies_list,
            description=description,
            directory=directory,
            documentation_url=documentation_url,
            path_to_plugin=path_to_plugin,
            info_url=info_url,
            last_modified=last_modified,
            latest_version=latest_version,
            menu_layout=menu_layout_list,
            name=name,
            url=url,
            version=packaging.version.Version(version_str),
        )


def get_plugin_info_from_url(info_url: str) -> PluginInfo | urllib.error.HTTPError:
    info_xml_str = get_plugin_info_xml_from_url(info_url)
    if isinstance(info_xml_str, urllib.error.HTTPError):
        return info_xml_str
    return PluginInfo.from_xml_str(info_xml_str)


def get_plugin_info_from_filesystem(
    plugin_dir_str: str,
) -> PluginInfo | FileNotFoundError:
    info_xml_fn = _get_path_to_plugin(plugin_dir_str) / "info.xml"
    if not info_xml_fn.exists():
        return FileNotFoundError(
            f"info.xml not found in {_get_path_to_plugin(plugin_dir_str)}"
        )
    with open(info_xml_fn, "r", encoding="utf-8") as f:
        info_xml_str = f.read()
    return PluginInfo.from_xml_str(info_xml_str)
