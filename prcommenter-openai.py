import os
import openai
import argparse
import json

from common import get_pr_diff, parse_diff, read_best_practices, post_github_comment, post_line_comments


def generate_review(diff, best_practices):
    print("Generating review from OpenAI...")
    prompt = f"""
You are a Java expert reviewing a GitHub pull request from a colleague. Below is the PR diff, with each line prefixed by a number in square brackets (`[]`):

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
  - **"line_number"** (int): The number inside `[]` at the start of the line.
  - **"comment"** (string): A **precise, markdown-styled review comment** with:
    - Clear improvement suggestions
    - Potential bug explanations
    - Code diffs/snippets when necessary
    - A friendly tone (smilies welcome! 😊)

#### Important:
- **Only provide the best comments**—if unsure, do **not** comment.
- The **only** output should be the structured **JSON response**.
    """

    response = openai.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "system", "content": "You are a helpful code reviewer."},
                  {"role": "user", "content": prompt}]
    )
    print(response)
    content = response.choices[0].message.content
    if content.startswith("```json\n"):
        content = content[8:]
    if content.endswith("```"):
        content = content[:-3]
    review = json.loads(content)
    print("Review generated successfully")
    return review


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
