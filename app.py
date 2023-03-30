import os,re
from flask import Flask, request
from github import Github, GithubIntegration

app = Flask(__name__)

app_id = 311892

# Read the bot certificate
with open(
        os.path.normpath(os.path.expanduser('bot-key.pem')),
        'r'
) as cert_file:
    app_key = cert_file.read()
    
# Create an GitHub integration instance
git_integration = GithubIntegration(
    app_id,
    app_key,
)

def issue_opened_event(repo, payload):
    issue = repo.get_issue(number=payload['issue']['number'])
    author = issue.user.login

    
    response = f"Thanks for opening this issue, @{author}! " \
                f"The repository maintainers will look into it ASAP! :speech_balloon:"
    issue.create_comment(f"{response}")
    issue.add_to_labels("pending")

def pull_request_merged(repo, payload):
    pullRequest = repo.get_pull(number=payload['pull_request']['number'])
    response = "Thanks for your contribution. Your pull request has been merged"
    pullRequest.create_issue_comment(f"{response}")

def deleteMergedBranch(repo, payload):
    branch = payload["pull_request"]["head"]["ref"]
    repo.get_git_ref(f"heads/{branch}").delete()

def isWIP(title):
    matches = re.findall("wip|work in progress|do not merge",title)
    return len(matches) > 0

def pendingPullRequest(repo, payload):
    pullRequest = repo.get_pull(number=payload['pull_request']['number'])
    sha = payload["pull_request"]["head"]["sha"]
    repo.get_commit(sha=sha).create_status(state="pending")



def successPullRequest(repo, payload):
    pullRequest = repo.get_pull(number=payload['pull_request']['number'])
    pullRequest.edit(state="success")

@app.route("/", methods=['POST'])
def bot():
    payload = request.json

    if not 'repository' in payload.keys():
        return "", 204

    owner = payload['repository']['owner']['login']
    repo_name = payload['repository']['name']

    git_connection = Github(
        login_or_token=git_integration.get_access_token(
            git_integration.get_installation(owner, repo_name).id
        ).token
    )
    repo = git_connection.get_repo(f"{owner}/{repo_name}")

    # Check if the event is a GitHub issue creation event
    if all(k in payload.keys() for k in ['action', 'issue']) and payload['action'] == 'opened':
        # Exercise 1
        issue_opened_event(repo, payload)


    # Check if the event is a pull request closed after been merged 
    if all(k in payload.keys() for k in ['action', 'pull_request']) and payload['action'] == 'closed':
        ismerge = payload['pull_request']['merged']
        if ismerge:
            # Exercise 2
            pull_request_merged(repo, payload)
            # Exercise 3
            deleteMergedBranch(repo, payload)


    # Exercise 4

    # Prevent merging of pull requests with "WIP" in the title when the pull request is created .
    if all(k in payload.keys() for k in ['action', 'pull_request']) and payload['action'] == 'opened':
        title = payload['pull_request']['title']
        if isWIP(title):
            pendingPullRequest(repo, payload)

    # Allow merging of pull request when "WIP" has been removed
    if all(k in payload.keys() for k in ['action', 'pull_request']) and payload['action'] == 'edited':
        title = payload['pull_request']['title']
        if isWIP(title):
            pendingPullRequest(repo, payload)
        else:
            successPullRequest(repo, payload)
    return "", 204

if __name__ == "__main__":
    app.run(debug=True, port=5000)
