import os
from enum import Enum

import requests
import json
import re

from pydantic import BaseModel

bot_prefix="🤖 [LabGpt] 🤖\n"

class PrCommentCategory(Enum):
    BUG = ("bug", "🐛")
    BEST_PRACTICE = ("best_practice", "✅")
    INCONSISTENCY = ("inconsistency", "⚠️")
    SECURITY_ISSUE = ("security_issue", "🔒")
    PERFORMANCE_ISSUE = ("performance_issue", "⏱️")
    NITPICKING = ("nitpicking", "🔍")
    AUDITING = ("auditing", "🕵️")
    OTHER = ("other", "ℹ️")

    def __init__(self, value, emoji):
        self._value_ = value
        self.emoji = emoji

    @classmethod
    def from_string(cls, value: str):
        """
        Convert a string to a PrCommentCategory Enum, case-insensitive
        """
        value = value.lower()
        for member in cls:
            if member.value == value:
                return member
        raise ValueError(f"No matching enum found for value {value}")

class PrComments(BaseModel):
    file: str
    line_number: int
    comment: str
    category: PrCommentCategory


def log_request_response(method, url, headers, data=None):
    print(
        f"\n--- HTTP REQUEST ---\nMethod: {method}\nURL: {url}\nHeaders: {json.dumps(headers, indent=2)}\nData: {json.dumps(data, indent=2) if data else 'None'}\n")

def log_response(response):
    print(f"\n--- HTTP RESPONSE ---\nStatus Code: {response.status_code}\nResponse Body: {response.text}\n")


def get_pr_diff(repo, pr_number, github_token):
    print(f"Fetching PR diff for {repo}#{pr_number}")
    url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}"
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3.diff"
    }
    log_request_response("GET", url, headers)
    response = requests.get(url, headers=headers)
    log_response(response)
    if response.status_code != 200:
        raise Exception(f"Failed to fetch diff: {response.status_code}")

    print("PR diff fetched successfully")
    return response.text


def get_pr_files(repo, pr_number, github_token):
    print(f"Fetching PR files for {repo} PR #{pr_number}")
    url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}/files"
    headers = {"Authorization": f"token {github_token}", "Accept": "application/vnd.github.v3+json"}
    log_request_response("GET", url, headers)
    response = requests.get(url, headers=headers)
    log_response(response)
    return response.json() if response.status_code == 200 else None


def get_pr_base_commit(repo, pr_number, github_token):
    """Fetches the base commit SHA for the PR."""
    print(f"Fetching base commit SHA for PR #{pr_number}")
    url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}"
    headers = {"Authorization": f"token {github_token}", "Accept": "application/vnd.github.v3+json"}
    log_request_response("GET", url, headers)
    response = requests.get(url, headers=headers)
    log_response(response)
    if response.status_code == 200:
        return response.json().get("base", {}).get("sha")
    return None


def get_file_content(repo, file_path, ref, github_token):
    """Fetches the content of a file from the repository at the given ref (commit SHA, branch, or tag)."""
    print(f"Fetching content for file: {file_path} at ref: {ref}")
    url = f"https://api.github.com/repos/{repo}/contents/{file_path}?ref={ref}"
    headers = {"Authorization": f"token {github_token}", "Accept": "application/vnd.github.v3.raw"}
    log_request_response("GET", url, headers)
    response = requests.get(url, headers=headers)
    log_response(response)
    return response.text if response.status_code == 200 else None


def get_original_files_content(repo, pr_number, github_token):
    """
    Fetches the original content of all files in a PR and concatenates them into a string.
    """
    print(f"Fetching original file contents for {repo} PR #{pr_number}")
    base_commit_sha = get_pr_base_commit(repo, pr_number, github_token)
    if not base_commit_sha:
        print("Failed to fetch base commit SHA.")
        return ""

    files = get_pr_files(repo, pr_number, github_token)
    if not files:
        return ""

    content_str = ""
    for file in files:
        file_path = file.get("filename")

        if file_path:
            file_content = get_file_content(repo, file_path, base_commit_sha, github_token)
            if file_content:
                content_str += f"\n\n--- FILE: {file_path} ---\n\n" + file_content
            else:
                print(f"Failed to fetch content for {file_path}")

    return content_str


def read_best_practices(file_path):
    print(f"Reading best practices from {file_path}")
    if file_path and os.path.exists(file_path):
        with open(file_path, "r") as file:
            return file.read()
    print("No best practices file found, proceeding without it.")
    return ""


def parse_diff(diff_text):
    """
    Parses the diff and assigns positions correctly, adding line numbers to each chunk.
    """
    diff_lines = diff_text.split('\n')
    old_position = 0
    new_position = 0
    processed_diff = []

    for line in diff_lines:
        if line.startswith("diff --git"):
            old_position = 0  # Reset position for a new file
            new_position = 0  # Reset position for a new file
        elif line.startswith("@@"):
            match = re.search(r"-(\d+).*\+(\d+)", line)  # Find a number after "-" and before ","
            old_position = int(match.group(1))-1
            new_position = int(match.group(2))-1
        elif line.startswith("-"):
            old_position += 1
        elif line.startswith("+"):
            new_position += 1
        else:
            old_position += 1
            new_position += 1

        if line.startswith("+"):
            processed_diff.append(f"[{new_position}] {line}")
        elif line.startswith("-"):
            processed_diff.append(f"[{old_position}] {line}")
        else:
            processed_diff.append(f"[{new_position}] {line}")


    parsed_diff_string = '\n'.join(processed_diff)
    print("Parsed diff:")
    print(parsed_diff_string)
    return parsed_diff_string

def post_github_comment(repo, pr_number, github_token, comment):
    print("Posting general review comment...")
    url = f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments"
    headers = {"Authorization": f"token {github_token}", "Accept": "application/vnd.github.v3+json"}
    data = {"body": f"{bot_prefix}{str(comment)}"}
    response = requests.post(url, json=data, headers=headers)
    log_response(response)
    if response.status_code != 201:
        raise Exception(f"Failed to post comment: {response.status_code}, {response.json()}")
    print("General review comment posted successfully.")


def get_latest_commit_sha(repo, pr_number, github_token):
    url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}/commits"
    headers = {"Authorization": f"token {github_token}"}
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        raise Exception(f"Failed to fetch commits: {response.status_code}, {response.json()}")

    commits = response.json()
    latest_commit_sha = commits[-1]["sha"]
    print(f"Latest commit SHA: {latest_commit_sha}")
    return latest_commit_sha


def post_line_comments(repo, pr_number, github_token, line_comments):
    print("Posting line-specific comments...")
    url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}/comments"
    headers = {"Authorization": f"token {github_token}", "Accept": "application/vnd.github.v3+json"}

    latest_commit_sha = get_latest_commit_sha(repo, pr_number, github_token)

    for comment in line_comments:
        print(f"Posting comment on {comment['file']} line {comment['line_number']}")
        data = {
            "body": f"{bot_prefix}{PrCommentCategory.from_string(comment["category"]).emoji} {comment["comment"]}",
            "commit_id": latest_commit_sha,
            "path": comment["file"],
            "line": int(comment["line_number"])
        }
        log_request_response("POST", url, headers, data)
        response = requests.post(url, json=data, headers=headers)
        log_response(response)
        if response.status_code != 201:
            print(f"Failed to post line comment: {response.status_code}, {response.json()}")
        else:
            print("Line comment posted successfully.")
