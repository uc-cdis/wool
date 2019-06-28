# wool

Utility binaries for linting python code using [black](https://github.com/ambv/black).

## Automatically Comment GitHub PRs with Travis

Wool can be automated using Travis to automatically comment on GitHub pull
requests to suggest formatting changes.

Add these lines to the `.travis.yml` file (each section can include other lines
as well, for example python 2.7, but these ones must be present for it to
work):
```
python:
  - "3.6"

env:
  - REPOSITORY="<username>/<repository>" PR_NUMBER="$TRAVIS_PULL_REQUEST"

install:
  - if [[ $TRAVIS_PYTHON_VERSION == 3.6 ]]; then pip install -e git+https://git@github.com/uc-cdis/wool.git#egg=wool; fi

after_script:
  - if [[ $TRAVIS_PYTHON_VERSION == 3.6 && $PR_NUMBER != false ]]; then wool; fi
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

## Automatically Comment GitHub PRs with a GitHub action workflow


Wool can be added as an action in a GitHub action workflow to automatically comment on GitHub pull
requests to suggest formatting changes.

```
workflow "Run python formatter" {
  on = "pull_request"
  resolves = ["Run wool"]
}

action "Run wool" {
  uses = "uc-cdis/wool@master"
  secrets = ["GITHUB_TOKEN"]
}
```
