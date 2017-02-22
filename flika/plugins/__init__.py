import pkg_resources, os

plugin_list = {
'Global Analysis': 'https://raw.githubusercontent.com/BrettJSettle/GlobalAnalysisPlugin/master/info.xml',
'Beam Splitter': 'https://raw.githubusercontent.com/BrettJSettle/BeamSplitter/master/info.xml',
'Rodent Tracker': 'https://raw.githubusercontent.com/kyleellefsen/rodentTracker/master/info.xml',
'Detect Puffs': 'https://raw.githubusercontent.com/kyleellefsen/detect_puffs/master/info.xml',
'Drift Correction': 'https://raw.githubusercontent.com/BrettJSettle/DriftCorrection/master/info.xml',
'Pynsight' : 'http://raw.githubusercontent.com/kyleellefsen/pynsight/master/info.xml'
}

def plugin_path(plugin_name=''):
    try:
        if pkg_resources.resource_exists('flika.plugins', plugin_name):
            return pkg_resources.resource_filename('flika.plugins', plugin_name)
        else:
            raise RuntimeError("plugin does not exist: %s" % plugin_name)
    except NotImplementedError:  # workaround for mac app
        result = os.path.dirname(__file__)
        return os.path.join(result.replace('site-packages.zip', 'flika'),
                            'plugins', plugin_name)
