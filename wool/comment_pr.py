import os
import subprocess
import sys

import requests


SIGNATURE = (
    "This formatting comment was generated automatically by a script in"
    " [uc-cdis/wool](https://github.com/uc-cdis/wool)."
)


def check_python_version():
    if sys.version_info.major < 3 or sys.version_info.minor < 6:
        raise EnvironmentError("wool requires python >= 3.6")


def black_comment_text(black_output):
    if black_output:
        return (
            "This PR contains code that is not formatted correctly according"
            " to [`black`](https://github.com/ambv/black). Run `black` on your"
            " code before merging.\n"
            "\n"
            "<details>\n"
            "<summary>Expand the full diff to see formatting changes</summary>\n"
            "\n"
            "```diff\n"
            "{}"
            "```\n"
            "</details></br>\n"
            "\n"
            "{}"
        ).format(black_output, SIGNATURE)
    else:
        return (
            "The style in this PR agrees with [`black`](https://github.com/ambv/black)."
            " :heavy_check_mark:\n"
            "\n"
            "{}"
        ).format(SIGNATURE)


def find_old_comment_url(comments_info):
    """
    comments_info should be the JSON response from:

        /{org}/{repo}/issues/{PR}/comments
    """
    for comment in comments_info:
        if SIGNATURE in comment["body"]:
            return comment["url"]
    return None


def comment_pr():
    check_python_version()

    try:
        # REPOSITORY should be the organization name, followed by a slash, followed
        # by the name of the specific repo. For example this repository would be
        # "uc-cdis/wool".
        repo = os.environ.get("GITHUB_REPOSITORY") or os.environ.get("REPOSITORY")
        if not repo:
            raise EnvironmentError("missing GITHUB_REPOSITORY environment variable")
        repo = repo.strip("/")
        pr_number = os.environ["PR_NUMBER"]
        github_token = os.environ["GITHUB_TOKEN"]
    except KeyError:
        raise EnvironmentError("missing environment variables")

    print(f"running wool for {repo}, PR #{pr_number}")

    base_url = "https://api.github.com/repos/{}".format(repo)
    pr_url = base_url + "/pulls/{}".format(pr_number)
    issue_url = base_url + "/issues/{}".format(pr_number)  # for comments
    comments_url = issue_url + "/comments"
    pr_files_url = pr_url + "/files"
    headers = {"Authorization": "token {}".format(github_token)}

    files = requests.get(pr_files_url, headers=headers).json()
    if not isinstance(files, list):
        print(files)
        raise Exception("Unable to get PR files")
    files_raw_urls = [file_info["raw_url"] for file_info in files]
    files_raw_contents = [
        requests.get(url, headers=headers).text for url in files_raw_urls
    ]

    output = []
    write = output.append
    python_files = [f for f in files if f["filename"].endswith(".py")]
    if not python_files:
        print("no python files to check")
        return
    files_str = "\n".join("    {}".format(f["filename"]) for f in files)
    print("checking files:\n{}".format(files_str))
    for file_info in python_files:
        filename = file_info["filename"]
        raw_url = file_info["raw_url"]
        raw_contents = requests.get(raw_url, headers=headers).text
        black = subprocess.run(
            ["black --diff - 2>/dev/null"],
            shell=True,
            input=raw_contents,
            encoding="ascii",
            stdout=subprocess.PIPE,
        )
        black_output = "\n".join(black.stdout.split("\n")[2:])
        if black_output:
            write("--- {}".format(filename))
            write("+++ blackened")
            write(black_output)

    full_output = "\n".join(output)
    comment_body = black_comment_text(full_output)
    comments_info = requests.get(comments_url, headers=headers).json()
    old_comment_url = find_old_comment_url(comments_info)
    if not old_comment_url:
        response = requests.post(
            comments_url, json={"body": comment_body}, headers=headers
        )
        if response.status_code != 201:
            print("failed to write comment", file=sys.stderr)
            print(response.json(), file=sys.stderr)
            return
    else:
        response = requests.patch(
            old_comment_url, json={"body": comment_body}, headers=headers
        )
        if response.status_code != 200:
            print("failed to edit comment", file=sys.stderr)
            print(response.json(), file=sys.stderr)
            return
