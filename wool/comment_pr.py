import json
import os
import re
import subprocess
import sys
from time import sleep

import requests


SIGNATURE = (
    "This formatting comment was generated automatically by a script in"
    " [uc-cdis/wool](https://github.com/uc-cdis/wool)."
)


ASK_FOR_FORMAT_COMMIT = ["wool", "black", "please format my code"]


def main():
    """
    When triggered by pull request commits, runs comment_on_pr to comment
    on the PR with the necessary formatting changes.
    When triggered by pull request comments, runs commit_on_pr to make a
    commit with the necessary formatting changes.
    """
    event_name = os.environ.get("GITHUB_EVENT_NAME")
    print("GITHUB_EVENT_NAME:", event_name)
    if event_name == "issue_comment":
        commit_on_pr()
    else:
        # if not running in a GH workflow or if the workflow was not
        # triggered by a comment, just comment on the PR
        comment_on_pr()


def check_python_version():
    if sys.version_info.major < 3 or sys.version_info.minor < 6:
        raise EnvironmentError("wool requires python >= 3.6")


def black_comment_text(black_output):
    if black_output:
        return (
            "This PR contains code that is not formatted correctly according"
            " to [`black`](https://github.com/ambv/black). Run `black` on your"
            ' code before merging, or comment "wool" or "black" on this PR and'
            " I will format the code for you.\n"
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
    def __init__(self, event_type):
        try:
            self.github_token = os.environ["GITHUB_TOKEN"]
            # if run in a github workflow this file should exist. otherwise
            # we assume there will be environment variables specifying the
            # repository and PR number
            workflow_data_path = os.environ.get("GITHUB_EVENT_PATH")
            if workflow_data_path and os.path.exists(workflow_data_path):
                with open(workflow_data_path, "r") as f:
                    self.payload = json.loads(f.read())
                # payload contents doc: https://developer.github.com/v3/activity/events/types
                event_url = self.payload[event_type]["url"]
                # if triggered by a PR, event_url is /pulls/
                # if triggered by a comment, event_url is /issues/
                # We need both
                self.pr_url = event_url.replace("/issues/", "/pulls/")
                issue_url = event_url.replace("/pulls/", "/issues/")
                self.comments_url = issue_url + "/comments"
                self.base_url = re.sub("/pulls.*$", "", self.pr_url)
            else:
                self.repo = os.environ.get("REPOSITORY")
                if not self.repo:
                    self.repo = os.environ["GITHUB_REPOSITORY"]
                self.repo = self.repo.strip("/")
                self.pr_number = os.environ["PR_NUMBER"]
                self.base_url = "https://api.github.com/repos/{}".format(self.repo)
                self.pr_url = self.base_url + "/pulls/{}".format(self.pr_number)
                issue_url = self.base_url + "/issues/{}".format(
                    self.pr_number
                )  # for comments
                self.comments_url = issue_url + "/comments"
            self.pr_files_url = self.pr_url + "/files"
            self.headers = {"Authorization": "token {}".format(self.github_token)}
        except KeyError as e:
            raise EnvironmentError(f"missing environment variable: {e}")


def run_black(github, diff_only):
    """
    Args:
        github (GitHubInfo)
        diff_only (bool): whether to return formatting diff or formatted files

    Returns:
        dict: file name to formatted contents (or to contents that should be
        formatted, if diff_only is True)
    """
    check_python_version()

    print(f"running wool for {github.pr_url}")

    # get files from PR
    files = requests.get(github.pr_files_url, headers=github.headers).json()
    if not isinstance(files, list):
        print(files)
        raise Exception("Unable to get PR files")
    files_raw_urls = [file_info["raw_url"] for file_info in files]
    files_raw_contents = [
        requests.get(url, headers=github.headers).text for url in files_raw_urls
    ]

    python_files = [f for f in files if f["filename"].endswith(".py")]
    if not python_files:
        print("no python files to check")
        return
    files_str = "\n".join("    {}".format(f["filename"]) for f in files)
    print("checking files:\n{}".format(files_str))

    # run black on the files
    file_to_black = {}
    for file_info in python_files:
        filename = file_info["filename"]
        raw_url = file_info["raw_url"]
        response = requests.get(raw_url, headers=github.headers)
        if response.status_code != 200:
            raise Exception(
                "Unable to get file `{}` at `{}`: got code {}.".format(
                    filename, raw_url, response.status_code
                )
            )
        raw_contents = response.text

        black_command = (
            "black --diff - 2>/dev/null" if diff_only else "black - 2>/dev/null"
        )
        black_result = subprocess.run(
            [black_command],
            shell=True,
            input=raw_contents,
            encoding="ascii",
            stdout=subprocess.PIPE,
        )

        if black_result.stdout != raw_contents:
            file_to_black[filename] = black_result.stdout

    return file_to_black


def comment_on_pr(github=None):
    """
    Comment on the PR with the formatting that should be fixed
    """
    github = github or GitHubInfo(event_type="pull_request")
    black_output = run_black(github, diff_only=True)

    output = []
    write = output.append
    status = "success"  # switch to failure if diff found
    for filename, black_diff in black_output.items():
        black_output = "\n".join(black_diff.split("\n")[2:])
        if black_output:
            status = "failure"
            write("--- {}".format(filename))
            write("+++ blackened")
            write(black_output)
    full_output = "\n".join(output)

    comment_body = black_comment_text(full_output)
    comments_info = requests.get(github.comments_url, headers=github.headers).json()
    old_comment = find_old_comment(comments_info)
    status_target_url = None
    if not old_comment:
        response = requests.post(
            github.comments_url, json={"body": comment_body}, headers=github.headers
        )
        if response.status_code != 201:
            print("failed to write comment", file=sys.stderr)
            print(response.json(), file=sys.stderr)
            return
        status_target_url = response.json()["html_url"]
    else:
        old_comment_url = old_comment.get("url")
        response = requests.patch(
            old_comment_url, json={"body": comment_body}, headers=github.headers
        )
        if response.status_code != 200:
            print("failed to edit comment", file=sys.stderr)
            print(response.json(), file=sys.stderr)
            return
        status_target_url = old_comment["html_url"]

    # add status check to the pull request
    pr_info = requests.get(github.pr_url, headers=github.headers).json()
    status_url = github.base_url + "/statuses/{}".format(pr_info["head"]["sha"])
    description = "Very stylish" if status == "success" else "Needs formatting"
    status_body = {
        "state": status,
        "target_url": status_target_url,
        "description": description,
        "context": "wool",
    }
    response = requests.post(status_url, json=status_body, headers=github.headers)
    if response.status_code != 201:
        print(f"failed to add status check ({status_url})", file=sys.stderr)
        print(response.json(), file=sys.stderr)
        return


def commit_on_pr():
    """
    Create a commit on the PR to fix the formatting
    """
    github = GitHubInfo(event_type="issue")

    # check if the comment is asking wool to format the code
    comment_contents = github.payload["comment"]["body"]
    if comment_contents.lower() not in ASK_FOR_FORMAT_COMMIT:
        return

    black_output = run_black(github, diff_only=False)
    if not black_output:
        print("No changes to commit")
        return

    # get latest commit on the PR
    commits_url = "https://api.github.com/repos/paulineribeyre/tests/git/commits"
    pr_info = requests.get(github.pr_url, headers=github.headers).json()
    latest_commit_sha = pr_info["head"]["sha"]
    response = requests.get(
        commits_url + "/" + latest_commit_sha, headers=github.headers
    )
    if response.status_code != 200:
        print("failed to get latest commit info", file=sys.stderr)
        print(response.json(), file=sys.stderr)
        return
    latest_commit_tree_sha = response.json()["tree"]["sha"]

    # get branch for this commit
    branch_url = "https://api.github.com/repos/paulineribeyre/tests/commits/{}/branches-where-head".format(
        latest_commit_sha
    )

    # endpoint "branches-where-head" is in beta
    headers = github.headers.copy()
    headers["Accept"] = "application/vnd.github.groot-preview+json"

    response = requests.get(branch_url, headers=headers)
    if response.status_code != 200:
        print("failed to get commit branch", file=sys.stderr)
        print(response.json(), file=sys.stderr)
        return
    branches = response.json()

    if len(branches) != 1:
        if len(branches) > 1:
            print(
                "Commit {} is the head of several branches. I don't know which one to update - exiting early".format(
                    latest_commit_sha
                )
            )
        else:
            print(
                "Commit {} is not the head of the branch. Assuming a new commit has been pushed - exiting early".format(
                    latest_commit_sha
                )
            )
        return

    branch_name = branches[0]["name"]

    # create new tree. it contains the formatted files
    trees_url = "https://api.github.com/repos/paulineribeyre/tests/git/trees"
    new_tree_body = {
        "tree": [
            {"content": contents, "path": filename, "mode": "100644", "type": "blob"}
            for filename, contents in black_output.items()
        ],
        "base_tree": latest_commit_tree_sha,
    }
    response = requests.post(trees_url, headers=github.headers, json=new_tree_body)
    if response.status_code != 201:
        print("failed to create new tree", file=sys.stderr)
        print(response.json(), file=sys.stderr)
        return
    new_tree_sha = response.json()["sha"]

    # create new commit
    new_commit_body = {
        "tree": new_tree_sha,
        "parents": [latest_commit_sha],
        "message": "Wool auto formatting",
    }
    response = requests.post(commits_url, headers=github.headers, json=new_commit_body)
    if response.status_code != 201:
        print("failed to create new commit", file=sys.stderr)
        print(response.json(), file=sys.stderr)
        return
    new_commit_sha = response.json()["sha"]

    # add the commit to the branch
    refs_url = (
        "https://api.github.com/repos/paulineribeyre/tests/git/refs/heads/"
        + branch_name
    )
    new_ref_body = {"sha": new_commit_sha}
    response = requests.patch(refs_url, headers=github.headers, json=new_ref_body)
    if response.status_code != 200:
        print("failed to create new ref", file=sys.stderr)
        print(response.json(), file=sys.stderr)
        return

    print("Pushed commit {} to branch {}".format(new_commit_sha, branch_name))

    # manually trigger comment update and status check, since wool's
    # commits don't trigger the pull_request workflow
    sleep(3)  # wait for the commit to show up in GitHub...
    comment_on_pr(github)
