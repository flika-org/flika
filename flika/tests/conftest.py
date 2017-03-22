import pytest
from ..app.application import FlikaApplication
flikaApp = FlikaApplication()

@pytest.fixture(scope='session', autouse=True)
def fa():
	return flikaApp