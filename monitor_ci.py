import os
import requests
import time
import sys
from datetime import datetime, timedelta

def get_token():
    env_path = os.path.expanduser("~/.hermes/.env")
    if not os.path.exists(env_path):
        return None
    with open(env_path, "r") as f:
        for line in f:
            if line.strip().startswith("GITHUB_TOKEN="):
                return line.split("=", 1)[1].strip()
    return None

def monitor(repo, branch="master"):
    token = get_token()
    if not token:
        print("Error: GITHUB_TOKEN not found.")
        return

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    url = f"https://api.github.com/repos/{repo}/actions/runs?branch={branch}&per_page=1"
    
    print(f"Monitoring CI for {repo} on branch {branch}...")
    
    # Wait for the run to appear (it might take a few seconds after push)
    start_wait = time.time()
    run_id = None
    while time.time() - start_wait < 60:
        resp = requests.get(url, headers=headers)
        if resp.status_code == 200:
            runs = resp.json().get("workflow_runs", [])
            if runs:
                latest_run = runs[0]
                created_at = datetime.strptime(latest_run["created_at"], "%Y-%m-%dT%H:%M:%SZ")
                # If created in the last 5 minutes, assume it's ours
                if datetime.utcnow() - created_at < timedelta(minutes=5):
                    run_id = latest_run["id"]
                    print(f"Found run ID: {run_id}, status: {latest_run['status']}")
                    break
        time.sleep(10)
    
    if not run_id:
        print("Error: Could not find a recent CI run.")
        return

    # Poll until completed
    while True:
        resp = requests.get(f"https://api.github.com/repos/{repo}/actions/runs/{run_id}", headers=headers)
        if resp.status_code == 200:
            run_data = resp.json()
            status = run_data["status"]
            conclusion = run_data.get("conclusion")
            
            print(f"Status: {status}, Conclusion: {conclusion}")
            
            if status == "completed":
                if conclusion == "success":
                    print("CI PASSED!")
                    sys.exit(0)
                else:
                    print(f"CI FAILED! Conclusion: {conclusion}")
                    # Fetch jobs to get more info
                    jobs_resp = requests.get(run_data["jobs_url"], headers=headers)
                    if jobs_resp.status_code == 200:
                        jobs = jobs_resp.json().get("jobs", [])
                        for job in jobs:
                            if job["conclusion"] == "failure":
                                print(f"Job '{job['name']}' failed. ID: {job['id']}")
                                # Note: Actual logs are binary/zipped via API, often easier to just say which job failed
                    sys.exit(1)
        
        time.sleep(30)

if __name__ == "__main__":
    monitor("dabendan2/chat-agent")
