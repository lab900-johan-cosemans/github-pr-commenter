import os
import requests
import json
import argparse
import google.generativeai as genai


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
    position = 0
    processed_diff = []

    for line in diff_lines:
        if line.startswith("diff --git"):
            position = 0  # Reset position for a new file
        elif line.startswith("@@"):
            position = 0  # Reset position at the start of a new hunk
        else:
            position += 1  # Count lines relative to the last @@

        processed_diff.append(f"[{position}] {line}")

    parsed_diff_string = '\n'.join(processed_diff)
    print("Parsed diff:")
    print(parsed_diff_string)
    return parsed_diff_string


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
    return response.text


def generate_review_comments(diff):
    model = genai.GenerativeModel("gemini-pro")
    prompt = f"Analyze the following GitHub pull request diff and provide a constructive review with comments:\n{diff}"
    response = model.generate_content(prompt)
    return response.text if response else "No response from Gemini."


def post_github_comment(repo, pr_number, github_token, comment):
    print("Posting general review comment...")
    url = f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments"
    headers = {"Authorization": f"token {github_token}", "Accept": "application/vnd.github.v3+json"}
    data = {"body": str(comment)}
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
            "body": comment["comment"],
            "commit_id": latest_commit_sha,
            "path": comment["file"],
            "position": int(comment["line_number"]),
            "subject_type": "line"
        }
        log_request_response("POST", url, headers, data)
        response = requests.post(url, json=data, headers=headers)
        log_response(response)
        if response.status_code != 201:
            print(f"Failed to post line comment: {response.status_code}, {response.json()}")
        else:
            print("Line comment posted successfully.")
