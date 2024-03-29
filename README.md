# wool

Utility binaries for linting python code using [black](https://github.com/ambv/black).

## Automatically Comment on GitHub PRs with Travis

Wool can be automated using Travis to automatically comment on GitHub pull
requests to suggest formatting changes.

Add these lines to the `.travis.yml` file (each section can include other lines
as well, for example python 2.7, but these ones must be present for it to
work):
```
python:
  - "3.9"

env:
  - REPOSITORY="<username>/<repository>" PR_NUMBER="$TRAVIS_PULL_REQUEST"

install:
  - if [[ $TRAVIS_PYTHON_VERSION == 3.9 ]]; then pip install -e git+https://git@github.com/uc-cdis/wool.git#egg=wool; fi

after_script:
  - if [[ $TRAVIS_PYTHON_VERSION == 3.9 && $PR_NUMBER != false ]]; then wool; fi
```
where `<username>/<repository>` in the line `- REPOSITORY=...` is as it is in
the GitHub URL. For example, for wool this would be `uc-cdis/wool`. Everything
else is literal.

After this, you should see comments like this one on your pull requests with good formatting:
```
The style in this PR agrees with [`black`](https://github.com/ambv/black). :heavy_check_mark:

This formatting comment was generated automatically by a script in [uc-cdis/wool](https://github.com/uc-cdis/wool).
```
And like this one, if changes are necessary:
````
This PR contains code that is not formatted correctly according to [`black`](https://github.com/ambv/black). Run `black` on your code before merging.

<details>
<summary>Expand the full diff to see formatting changes</summary>

```diff
--- file.py
+++ blackened
 ... diff here ...
```
</details></br>

This formatting comment was generated automatically by a script in [uc-cdis/wool](https://github.com/uc-cdis/wool).
````

## Automatically Comment on GitHub PRs with a GitHub action workflow

Wool can be added as an action in a GitHub action workflow to automatically comment on GitHub pull
requests to suggest formatting changes.

```
on: pull_request

name: Wool

jobs:
  runWool:
    name: Run black
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@master

    - uses: uc-cdis/wool@master
      env:
        GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```


## Automatically Commit on GitHub PRs with a GitHub action workflow

Wool can be added as an action in a GitHub action workflow to make formatting commits on pull requests. Users can request a formatting commit by commenting "wool", "black" or "please format my code" on a pull request.

```
on:
  issue_comment:
    types: [created, edited]

name: Wool

jobs:
  runWool:
    name: Auto format
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@master

    - uses: uc-cdis/wool@master
      env:
        GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

Commenting and committing can be enabled in a single workflow by using:

```
on:
  pull_request:
  issue_comment:
    types: [created, edited]
```
