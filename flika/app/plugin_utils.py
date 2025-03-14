import beartype
import dataclasses
import pathlib
import packaging.version
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ElementTree


plugin_info_urls_by_name = {
    'Beam Splitter':    'https://raw.githubusercontent.com/BrettJSettle/BeamSplitter/master/',
    'Detect Puffs':     'https://raw.githubusercontent.com/kyleellefsen/detect_puffs/master/',
    'Global Analysis':  'https://raw.githubusercontent.com/BrettJSettle/GlobalAnalysisPlugin/master/',
    'Pynsight':         'http://raw.githubusercontent.com/kyleellefsen/pynsight/master/',
    'QuantiMus':        'http://raw.githubusercontent.com/Quantimus/quantimus/master/',
    'Rodent Tracker':   'https://raw.githubusercontent.com/kyleellefsen/rodentTracker/master/'
}

@beartype.beartype
def get_plugin_info_xml_from_url(info_url: str) -> str | urllib.error.HTTPError:
    info_url_xml : str = urllib.parse.urljoin(info_url, 'info.xml')
    try:
        info_xml_bytes : bytes = urllib.request.urlopen(info_url_xml).read()
        info_xml_str : str = info_xml_bytes.decode('utf-8')
    except urllib.error.HTTPError as e:
        return e
    return info_xml_str

@beartype.beartype
def parse_plugin_info_xml(xml_str: str) -> dict:
    """
    Parse an XML string into a dictionary.
    """
    #logger.debug('Calling app.plugin_manager.parse')
    tree = ElementTree.fromstring(xml_str)
    def step(item: ElementTree.Element) -> dict:
        d = {}
        if item.text and item.text.strip():
            d['#text'] = item.text.strip()
        for k, v in item.items():
            d[f'@{k}'] = v
        for k in list(item):
            if k.tag not in d:
                d[k.tag] = step(k)
            elif isinstance(d[k.tag], list):
                d[k.tag].append(step(k))
            else:
                d[k.tag] = [d[k.tag], step(k)]
        if len(d) == 1 and '#text' in d:
            return d['#text']
        return d
    return step(tree)


@beartype.beartype
@dataclasses.dataclass(frozen=True)
class PluginInfo:
    author: str  # The author of the plugin
    dependencies: list[str]  # The dependencies of the plugin
    description: str  # The description of the plugin
    directory: str  # The name of the module to import. This will be changed to 'module_name' eventually.
    documentation: str  # The documentation of the plugin
    full_path: pathlib.Path  # The full path to the plugin directory    
    info_url: str  # The URL of the plugin info
    last_modified: float  # The last modified date of the plugin
    latest_version: packaging.version.Version  # The latest version of the plugin
    menu_layout: list[dict]  # The menu layout of the plugin
    name: str  # The human-readable name of the plugin
    url: str  # The URL of the plugin
    version: packaging.version.Version  # The version of the plugin

    @classmethod
    def from_xml_str(cls, xml_str: str) -> 'PluginInfo':
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
        name = plugin_dict.get('@name', '')
        
        # Extract other required fields, stripping whitespace
        directory = plugin_dict.get('directory', '').strip()
        version_str = plugin_dict.get('version', '0.0.0').strip()
        author = plugin_dict.get('author', '').strip()
        url = plugin_dict.get('url', '').strip()
        
        # Parse dependencies - If dependencies is a dict with dependency elements
        dependencies_list = []
        dependencies = plugin_dict.get('dependencies', {})
        if isinstance(dependencies, dict):
            # When there's a single dependency, it will be a dict
            if 'dependency' in dependencies:
                dependency = dependencies['dependency']
                if isinstance(dependency, dict) and '@name' in dependency:
                    dependencies_list.append(dependency['@name'])
                elif isinstance(dependency, list):
                    # Multiple dependencies as a list
                    for dep in dependency:
                        if isinstance(dep, dict) and '@name' in dep:
                            dependencies_list.append(dep['@name'])
        
        # Parse menu_layout - actions with their properties
        menu_layout_list = []
        menu_layout = plugin_dict.get('menu_layout', {})
        if isinstance(menu_layout, dict) and 'action' in menu_layout:
            actions = menu_layout['action']
            if isinstance(actions, dict):
                # Single action
                menu_layout_list.append(actions)
            elif isinstance(actions, list):
                # Multiple actions
                menu_layout_list.extend(actions)
        
        # Providing default values for required fields not in the XML
        description = plugin_dict.get('description', '')
        documentation = plugin_dict.get('documentation', '')
        full_path = pathlib.Path(directory) if directory else pathlib.Path('.')
        info_url = plugin_dict.get('info_url', '')
        last_modified = float(plugin_dict.get('last_modified', 0))
        latest_version = packaging.version.Version(plugin_dict.get('latest_version', version_str))
        
        # Create and return the PluginInfo object
        return cls(
            author=author,
            dependencies=dependencies_list,
            description=description,
            directory=directory,
            documentation=documentation,
            full_path=full_path,
            info_url=info_url,
            last_modified=last_modified,
            latest_version=latest_version,
            menu_layout=menu_layout_list,
            name=name,
            url=url,
            version=packaging.version.Version(version_str)
        )

def get_plugin_info_from_url(info_url: str) -> PluginInfo | urllib.error.HTTPError:
    info_xml_str = get_plugin_info_xml_from_url(info_url)
    if isinstance(info_xml_str, urllib.error.HTTPError):
        return info_xml_str
    return PluginInfo.from_xml_str(info_xml_str)

def get_plugin_info_from_filesystem(plugin_dir: pathlib.Path) -> PluginInfo | FileNotFoundError:
    info_xml_fn = plugin_dir / 'info.xml'
    if not info_xml_fn.exists():
        return FileNotFoundError(f"info.xml not found in {plugin_dir}")
    with open(info_xml_fn, 'r', encoding='utf-8') as f:
        info_xml_str = f.read()
    return PluginInfo.from_xml_str(info_xml_str)

def main():
    info_url = plugin_info_urls_by_name['Pynsight']
    info_xml_str = get_plugin_info_xml_from_url(info_url)
    print(info_xml_str)
    plugin_info = PluginInfo.from_xml_str(info_xml_str)
    print(plugin_info)

if __name__ == '__main__':
    main()