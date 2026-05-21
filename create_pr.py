import os
import json
import urllib.request
import subprocess

def create_pr():
    # Push the branch first (using subprocess to avoid bash wrapper issue)
    try:
        subprocess.run(['git', 'push', '--set-upstream', 'origin', 'test-interact-with'], check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        pass # It might fail if no origin exists in local environment, we'll try API anyway

    token = os.environ.get('GITHUB_TOKEN')
    repo = os.environ.get('GITHUB_REPOSITORY')

    if not token or not repo:
        print("Missing GITHUB_TOKEN or GITHUB_REPOSITORY environment variables.")
        return

    url = f"https://api.github.com/repos/{repo}/pulls"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    data = {
        "title": "🧪 Add tests and prevent self-interaction in Agent.interact_with",
        "head": "test-interact-with",
        "base": "main",
        "body": "🎯 **What:** The `interact_with` method in `Agent` lacked test coverage and allowed self-interactions.\n📊 **Coverage:** Added tests for new interactions, existing interactions, negative values, and self-interaction edge cases.\n✨ **Result:** `interact_with` is now thoroughly tested and safely ignores self-interactions, increasing simulation robustness."
    }

    req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers=headers, method='POST')
    try:
        with urllib.request.urlopen(req) as response:
            res_data = json.loads(response.read().decode('utf-8'))
            print(f"PR created successfully: {res_data.get('html_url')}")
    except Exception as e:
        print(f"Error creating PR: {e}")

create_pr()
