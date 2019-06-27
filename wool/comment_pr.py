import json
import os
import re
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


def find_old_comment(comments_info):
    """
    comments_info should be the JSON response from:

        /{org}/{repo}/issues/{PR}/comments
    """
    for comment in comments_info:
        if SIGNATURE in comment["body"]:
            return comment
    return None


class GitHubInfo(object):
    def __init__(self):
        try:
            self.github_token = os.environ["GITHUB_TOKEN"]
            # if run in a github workflow this file should exist. otherwise we assume
            # there will be environment variables specifying the repository and PR
            # number
            workflow_data_path = os.environ.get("GITHUB_EVENT_PATH")
            if workflow_data_path and os.path.exists(workflow_data_path):
                with open(workflow_data_path, "r") as f:
                    data = json.loads(f.read())
                self.pr_url = data["pull_request"]["url"]
                issue_url = data["pull_request"]["issue_url"]
                self.comments_url = issue_url + "/comments"
                self.base_url = re.sub("/pulls.*$", "", self.pr_url) # eww
            else:
                self.repo = os.environ.get("REPOSITORY")
                if not repo:
                    repo = os.environ["GITHUB_REPOSITORY"]
                self.repo = repo.strip("/")
                self.pr_number = os.environ["PR_NUMBER"]
                self.base_url = "https://api.github.com/repos/{}".format(repo)
                self.pr_url = base_url + "/pulls/{}".format(pr_number)
                issue_url = base_url + "/issues/{}".format(pr_number)  # for comments
                self.comments_url = issue_url + "/comments"
            self.pr_files_url = self.pr_url + "/files"
            self.headers = {"Authorization": "token {}".format(self.github_token)}
        except KeyError as e:
            raise EnvironmentError(f"missing environment variable: {e}")


def comment_pr():
    check_python_version()

    github = GitHubInfo()
    print(f"running wool for {github.pr_url}")
    files = requests.get(github.pr_files_url, headers=github.headers).json()
    if not isinstance(files, list):
        print(files)
        raise Exception("Unable to get PR files")
    files_raw_urls = [file_info["raw_url"] for file_info in files]
    files_raw_contents = [
        requests.get(url, headers=github.headers).text for url in files_raw_urls
    ]

    output = []
    write = output.append
    python_files = [f for f in files if f["filename"].endswith(".py")]
    if not python_files:
        print("no python files to check")
        return
    files_str = "\n".join("    {}".format(f["filename"]) for f in files)
    print("checking files:\n{}".format(files_str))
    status = "success" # switch to failure if diff found
    for file_info in python_files:
        filename = file_info["filename"]
        raw_url = file_info["raw_url"]
        raw_contents = requests.get(raw_url, headers=github.headers).text
        black = subprocess.run(
            ["black --diff - 2>/dev/null"],
            shell=True,
            input=raw_contents,
            encoding="ascii",
            stdout=subprocess.PIPE,
        )
        black_output = "\n".join(black.stdout.split("\n")[2:])
        if black_output:
            status = "failure"
            write("--- {}".format(filename))
            write("+++ blackened")
            write(black_output)

    full_output = "\n".join(output)
    comment_body = black_comment_text(full_output)
    comments_info = requests.get(github.comments_url, headers=github.headers).json()
    old_comment = find_old_comment(comments_info)
    old_comment_url = old_comment["url"]
    if not old_comment_url:
        response = requests.post(
            github.comments_url, json={"body": comment_body}, headers=github.headers
        )
        if response.status_code != 201:
            print("failed to write comment", file=sys.stderr)
            print(response.json(), file=sys.stderr)
            return
    else:
        response = requests.patch(
            old_comment_url, json={"body": comment_body}, headers=github.headers
        )
        if response.status_code != 200:
            print("failed to edit comment", file=sys.stderr)
            print(response.json(), file=sys.stderr)
            return

    # add status check to the pull request
    pr_info = requests.get(github.pr_url, headers=github.headers).json()
    status_url = github.base_url + "/statuses/{}".format(pr_info["head"]["sha"])
    description = "Very stylish" if status == "success" else "Needs formatting"
    status_body = {
        "state": status,
        "target_url": old_comment["html_url"],
        "description": description,
        "context": "wool",
    }
    response = requests.post(status_url, json=status_body, headers=github.headers)
    if response.status_code != 201:
        print(f"failed to add status check ({status_url})", file=sys.stderr)
        print(response.json(), file=sys.stderr)
        return
