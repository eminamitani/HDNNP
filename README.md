# High Dimensional Neural Network Potential(HDNNP)

> This is a implementation of High Dimensional Neural Network Potential(HDNNP) designed to reproduce Density Function Theory(DFT) calculation *effectively* with high *flexibility*, *reactivity*.

There is equivalent doc in Japanese [README.ja.md](https://github.com/ogura-edu/HDNNP/blob/master/README.ja.md).

## Install

Install this project by `git`.

```shell
git clone git@github.com:ogura-edu/HDNNP.git

# or if using ssh

git clone git@github.com:ogura-edu/HDNNP.git
```

This project uses [Pipenv](https://github.com/pypa/pipenv) for development workflow. If you don't have it, run this command to install.


**macOS**
```
brew install pipenv
```

## Setup
### By Pipenv(Prefered)

Same as by anaconda, but you need to install python rather than installing anaconda. This bug will be fixed in near future release.

Set environmental variable `PIPENV_VENV_IN_PROJECT` to `1` to create your VM into this project dir(`/path/to/HDNNP/.venv`).

```shell
export PIPENV_VENV_IN_PROJECT = 1
```

For macOS users, you need to install `mpich` before installing dependencies.

```shell
# Only for macOS users
$ brew install mpich

# Install dependencies
$ pipenv install

# activate your VM
$ pipenv shell

# deactivate
(HDNNP) $ exit
```


### By Anaconda

Using anaconda is prefered because it is basically faster than Pipenv.

Install anaconda and activate your VM.

```shell
$ ANACONDA_VERSION = [YOUR_ANACODA_VERSION]
$ pyenv install $ANACONDA_VERSION
$ pyenv local $ANACONDA_VERSION
$ conda env create -n HDNNP --file condaenv.yaml
$ echo ". ${HOME}/.pyenv/versions/<anacondaVERSION>/etc/profile.d/conda.sh" > ~/.bashrc

# activate
$ conda activate HDNNP

# install this program using pip
(HDNNP) $ pip install --editable .

# For example...
(HDNNP) $ hdnnpy training


# deactivate
(HDNNP) $ conda deactivate
```

**NOTE** 

There is no

- ChainerMN
- Chainer v5

on the Anaconda Cloud, so you still have to install these packages by `pip`.

And these is a bug that if you install anaconda by `pyenv`, `pipenv` will fail to start.

## Usage
### Generating XYZ file

For generating `.xyz` chemical format which is a starndard format for discribing molecule geometry, use `vasp2xyz.py`.

Run this command and you will get a `xyz` file.

```shell
./scripts/vasp2xyz [CONFIG] [OUTCAR] [XYZFILE]
```

Here are these args.

- `[CONFIG]`: To specify each output
- `[OUTCAR]`: Your path to OUTCAR
- `[XYZFILE]`: Your output

## Reference

- Jörg Behler. First Principle Neural Network Potentials for Reactive Simulations of Large Molecular and Condensed System, 2007
