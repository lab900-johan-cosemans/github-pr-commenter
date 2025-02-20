import os
import json
import argparse
from google import genai
from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()

from common import get_original_files_content, get_pr_diff, parse_diff, read_best_practices, post_github_comment, post_line_comments

class PrComments(BaseModel):
    file: str
    line_number: int
    comment: str

class PrFeedback(BaseModel):
    general_summary: str
    line_comments: list[PrComments]

def generate_review(diff, pr_file_string, best_practices):
    google_key = os.getenv("GOOGLE_API_KEY")

    client = genai.Client(api_key=google_key)


    print("Generating review from gemini...")
    prompt = f"""
### Context:
You are a software development team lead in the Engineering department of a technology/software company. 
Generate a checklist that developers can use when conducting code reviews. 
The checklist should give feedback for code structure, readability, error handling, documentation, performance, security, and adherence to coding standards. 
Ensure that the checklist covers important aspects of code quality and provides guidance for thorough and effective code reviews.
Only add comments for important improvements, potential bugs, or best practices.
There is no need for picky details or positive remarks; focus on the most critical issues.

Below is the following:
1. Between the `----DIFF START----` and `----DIFF END----` lines, you will find the diff of the pull request, with each line prefixed by a number in square brackets (`[]`):
2. Between the `----SOURCEFILESSTART----` and `----SOURCEFILESEND----` lines, you will find the content of the source files in the pull request.
3. Between the `----CODINGPRACTICES----` and `----CODINGPRACTICES----` lines, you will find the best practices for our developers.

### Goal:
Provide a **structured JSON response** with:

- **"general_summary"** (string): A **concise, markdown-styled summary** of the most important changes. Keep it **short, structured, and easy to read**, using bullets if necessary.
- **"line_comments"** (list of objects): Only include **high-quality, relevant, and actionable comments** for important improvements, potential bugs, or best practices. Each comment should contain:
  - **"file"** (string): The full file path relative to the repository root.
  - **"line_number"** (int): The number inside `[]` at the start of the line. Only include line_numbers available in the diff. Do **not** include line numbers for unchanged lines.
  - **"comment"** (string): A **precise, markdown-styled review comment** with:
    - Clear improvement suggestions
    - Potential bug explanations
    - Code diffs/snippets when necessary
    - A friendly tone (smilies welcome! 😊)

- **Only provide the best comments**—if unsure, do **not** comment.
- The **only** output should be the structured **JSON response**.

----DIFF START----
{diff}
----DIFF END----


----SOURCEFILESSTART----
{pr_file_string}
----SOURCEFILESEND----


----CODINGPRACTICES----
{best_practices}
----CODINGPRACTICES----


    """
    response = client.models.generate_content(
        model="gemini-2.0-flash-exp",
        config={
            'response_mime_type': 'application/json',
            'response_schema': PrFeedback,
        },
        contents=prompt,
    )

    content = response.text
    # trim content, remove whitespace and newline characters
    content = content.strip()
    if content.startswith("```json\n"):
        content = content[8:]
    if content.endswith("```"):
        content = content[:-3]

    print(content)
    review = json.loads(content)
    print("Review generated successfully")
    return review


def main():
    print("Starting PR review process...")
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True, help="GitHub repository (e.g., owner/repo)")
    parser.add_argument("--pr", required=True, help="Pull request number")
    parser.add_argument("--best-practices", help="Path to a text file with coding best practices")
    parser.add_argument("--dry-run", help="Only print the comments without actually posting them to github",default="false")
    args = parser.parse_args()

    # Set environment variable for the Gemini API key
    google_key = os.getenv("GOOGLE_API_KEY")
    if not google_key:
        raise Exception(
            "GOOGLE_API_KEY not found. Please set the GOOGLE_API_KEY environment variable.")

    github_token = os.getenv("GITHUB_API_TOKEN")
    if not github_token:
        raise Exception("GitHub API token not found. Please set the GITHUB_API_TOKEN environment variable.")

    print("Fetching PR diff...")
    pr_file_string = get_original_files_content(args.repo, args.pr, github_token)
    diff = get_pr_diff(args.repo, args.pr, github_token)
    parsed_diff = parse_diff(diff)
    best_practices = read_best_practices(args.best_practices)
    review = generate_review(parsed_diff, pr_file_string, best_practices)

    print("--- Review Output ---")
    print(json.dumps(review, indent=2))

    if args.dry_run == "false":
        post_github_comment(args.repo, args.pr, github_token, review["general_summary"])
        post_line_comments(args.repo, args.pr, github_token, review["line_comments"])

    print("PR review process completed successfully.")


if __name__ == "__main__":
    main()
