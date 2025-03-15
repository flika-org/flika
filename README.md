# flika

![flika screencapture](flika/docs/_static/img/flika_screencapture.gif)

**flika** is an interactive image processing program for biologists written in Python.

## Website
[flika-org.github.io](http://flika-org.github.io/)

## Documentation
[flika-org.github.io/contents.html](http://flika-org.github.io/contents.html)

## Install
[flika-org.github.io/getting-started.html#installation](http://flika-org.github.io/getting-started.html#installation)

## Development

This is how Kyle installs Flika for development on a mac.

```fish
brew install python@3.13
python3.13 -m venv ~/venvs/flika; source ~/venvs/flika/bin/activate.fish; python -m pip install --upgrade pip;
cd ~/git
git clone https://github.com/flika-org/flika.git
cd ~/git/flika
python -m pip install -e .
ipython
In [1]: import flika
In [2]: flika.start_flika()
```

For tests:
```fish
pip install -e .[dev]
pytest flika --cov=flika
```

Cleanup :
```fish
deactivate
rm -r ~/venvs/flika
```


## Contributors

- [Kyle Ellefsen](https://github.com/KyleEllefsen)
- [Brett Settle](https://github.com/BrettJSettle)
- [George Dickinson](https://github.com/gddickinson)
- [Kevin Tarhan](https://github.com/KevinTarhan)


