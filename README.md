# lds-tools

Scripts to mine information from LDS.org

`contact-info.py` takes a name as an argument and will return the contact
information of the people who match the string. There is an optional number of
errors argument that will allow you to be more or less strict with the matching.
The default is 3.

Note: You will need to download the client_secret.json from the Google API Console.

## install

- Use python 2.7.9

```
env PYTHON_CONFIGURE_OPTS="--enable-framework" pyenv install -v 2.7.9
```

- install packages

```
pip install gdata requests regex pyinstaller oauth2client
```

- run `install.sh`
