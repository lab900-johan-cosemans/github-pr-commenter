import os
import requests
import json
import argparse
from google.api_core import client_options as client_options_lib
from google.api_core import gapic_v1
from google.auth import credentials as ga_credentials
from google.oauth2 import service_account

# Set environment variable for the Gemini API key
credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
if not credentials_path:
    raise Exception("Google application credentials not found. Please set the GOOGLE_APPLICATION_CREDENTIALS environment variable.")

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
    if response.status_code!= 200:
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


def generate_review(diff, best_practices):
    print("Generating review from Gemini...")

    # Construct the prompt for Gemini
    prompt = f"""
You are a Java expert reviewing a GitHub pull request from a colleague. Below is the PR diff, with each line prefixed by a number in square brackets (``):

------
{diff}
------

### Coding Best Practices:
------
{best_practices}
------

### Instructions:
Provide a **structured JSON response** with:

- **"general_summary"** (string): A **concise, markdown-styled summary** of the most important changes. Keep it **short, structured, and easy to read**, using bullets if necessary.
- **"line_comments"** (list of objects): Only include **high-quality, relevant, and actionable comments** for important improvements, potential bugs, or best practices. Each comment should contain:
  - **"file"** (string): The full file path relative to the repository root.
  - **"line_number"** (int): The number inside `` at the start of the line.
  - **"comment"** (string): A **precise, markdown-styled review comment** with:
    - Clear improvement suggestions
    - Potential bug explanations
    - Code diffs/snippets when necessary
    - A friendly tone (smilies welcome! 😊)

#### Important:
- **Only provide the best comments**—if unsure, do **not** comment.
- The **only** output should be the structured **JSON response**.
    """

    # Initialize Gemini API client
    credentials = ga_credentials.AnonymousCredentials()
    api_endpoint = "generativelanguage.googleapis.com"
    client_options = client_options_lib.ClientOptions(api_endpoint=api_endpoint)
    gemini_client = service_account.Credentials.from_service_account_file(
        credentials_path,
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    transport = gapic_v1.Transport(
        options=client_options,
        credentials=gemini_client  # Using gemini_client here
    )
    gemini_client = transport.get_client(credentials=credentials)  # Assigning to gemini_client

    # Generate text with Gemini
    response = gemini_client.generate_text(
        model="models/gemini-pro",  # Use the appropriate Gemini model
        prompt=prompt
    )

    # Extract and parse the JSON response
    content = response.candidates.output
    if content.startswith("```json\n"):
        content = content[8:]
    if content.endswith("```"):
        content = content[:-3]
    review = json.loads(content)
    print("Review generated successfully")
    return review


def post_github_comment(repo, pr_number, github_token, comment):
    print("Posting general review comment...")
    url = f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments"
    headers = {"Authorization": f"token {github_token}", "Accept": "application/vnd.github.v3+json"}
    data = {"body": str(comment)}
    response = requests.post(url, json=data, headers=headers)
    log_response(response)
    if response.status_code!= 201:
        raise Exception(f"Failed to post comment: {response.status_code}, {response.json()}")
    print("General review comment posted successfully.")


def get_latest_commit_sha(repo, pr_number, github_token):
    url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}/commits"
    headers = {"Authorization": f"token {github_token}"}
    response = requests.get(url, headers=headers)

    if response.status_code!= 200:
        raise Exception(f"Failed to fetch commits: {response.status_code}, {response.json()}")

    commits = response.json()
    latest_commit_sha = commits[-1]["sha"]
    print(f"Latest commit SHA: {latest_commit_sha}")
    return latest_commit_sha


def get_diff_hunks(repo, pr_number, github_token):
    print("Fetching diff hunks...")
    url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}/files"
    headers = {"Authorization": f"token {github_token}"}
    response = requests.get(url, headers=headers)

    if response.status_code!= 200:
        raise Exception(f"Failed to fetch PR files: {response.status_code}, {response.json()}")

    files = response.json()
    diff_hunks = {}
    for file in files:
        filename = file["filename"]
        diff_hunks[filename] = file.get("patch", "")

    print("Diff hunks fetched successfully.")
    return diff_hunks


def post_line_comments(repo, pr_number, github_token, line_comments):
    print("Posting line-specific comments...")
    url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}/comments"
    headers = {"Authorization": f"token {github_token}", "Accept": "application/vnd.github.v3+json"}

    latest_commit_sha = get_latest_commit_sha(repo, pr_number, github_token)
    #    diff_hunks = get_diff_hunks(repo, pr_number, github_token)

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
        if response.status_code!= 201:
            print(f"Failed to post line comment: {response.status_code}, {response.json()}")
        else:
            print("Line comment posted successfully.")


def main():
    print("Starting PR review process...")
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True, help="GitHub repository (e.g., owner/repo)")
    parser.add_argument("--pr", required=True, help="Pull request number")
    parser.add_argument("--best-practices", help="Path to a text file with coding best practices")
    args = parser.parse_args()

    github_token = os.getenv("GITHUB_API_TOKEN")
    if not github_token:
        raise Exception("GitHub API token not found. Please set the GITHUB_API_TOKEN environment variable.")

    diff = get_pr_diff(args.repo, args.pr, github_token)
    parsed_diff = parse_diff(diff)
    best_practices = read_best_practices(args.best_practices)
    review = generate_review(parsed_diff, best_practices)

    print("--- Review Output ---")
    print(json.dumps(review, indent=2))

    post_github_comment(args.repo, args.pr, github_token, review["general_summary"])
    post_line_comments(args.repo, args.pr, github_token, review["line_comments"])

    print("PR review process completed successfully.")


if __name__ == "__main__":
    main()