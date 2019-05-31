# lds-tools

Scripts to mine information from LDS.org

`contact-info.py` takes a name as an argument and will return the contact
information of the people who match the string. There is an optional number of
errors argument that will allow you to be more or less strict with the matching.
The default is 3.

Note: You will need to download the client_secret.json from the Google API Console.

## Install

### Use Python 2.7.9
The Google Contacts libraries are finicky and I have only got things working on
a particular version.

```
env PYTHON_CONFIGURE_OPTS="--enable-framework" pyenv install -v 2.7.9
```

### Install Packages

```
pip install gdata requests regex oauth2client selenium
```

### Ensure Chrome WebDriver
You need to make sure that the Chrome WebDriver is downloaded to the root of the
project somewhere in the system path for selenium to be able to work. Follow
[this guide](http://chromedriver.chromium.org/getting-started) to download the
right version.

### Run `install.sh`
