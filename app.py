'''
Goal of Flask Microservice:
1. Flask will take the repository_name such as angular, angular-cli, material-design, D3 from the body of the api sent from React app and 
   will utilize the GitHub API to fetch the created and closed issues. Additionally, it will also fetch the author_name and other 
   information for the created and closed issues.
2. It will use group_by to group the data (created and closed issues) by month and will return the grouped data to client (i.e. React app).
3. It will then use the data obtained from the GitHub API (i.e Repository information from GitHub) and pass it as a input request in the 
   POST body to LSTM microservice to predict and forecast the data.
4. The response obtained from LSTM microservice is also return back to client (i.e. React app).

Use Python/GitHub API to retrieve Issues/Repos information of the past 1 year for the following repositories:
- https: // github.com/angular/angular
- https: // github.com/angular/material
- https: // github.com/angular/angular-cli
- https: // github.com/d3/d3

+++Added+++
- https://github.com/SebastianM/angular-google-maps
- https://github.com/facebook/react
- https://github.com/tensorflow/tensorflow
- https://github.com/keras-team/keras
- https://github.com/pallets/flask
'''

# Import all the required packages 
import os
from flask import Flask, jsonify, request, make_response, Response
from flask_cors import CORS
import json
import dateutil.relativedelta
from dateutil import *
from datetime import date
import pandas as pd
import requests

# Initilize flask app
app = Flask(__name__)
# Handles CORS (cross-origin resource sharing)
CORS(app)

# Add response headers to accept all types of  requests
def build_preflight_response():
    response = make_response()
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add("Access-Control-Allow-Headers", "Content-Type")
    response.headers.add("Access-Control-Allow-Methods",
                         "PUT, GET, POST, DELETE, OPTIONS")
    return response

# Modify response headers when returning to the origin
def build_actual_response(response):
    response.headers.set("Access-Control-Allow-Origin", "*")
    response.headers.set("Access-Control-Allow-Methods",
                         "PUT, GET, POST, DELETE, OPTIONS")
    return response

'''
API route path is  "/api/forecast"
This API will accept only POST request
'''
@app.route('/api/github', methods=['POST'])
def github():
    body = request.get_json()
    # Extract the choosen repositories from the request
    repo_name = body['repository']
    # Add your own GitHub Token to run it local
    token = os.environ.get(
        'GITHUB_TOKEN', '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')
    GITHUB_URL = f"https://api.github.com/"
    headers = {
        "Authorization": f'token {token}'
    }
    params = {
        "state": "open"
    }
    repository_url = GITHUB_URL + "repos/" + repo_name
    # Fetch GitHub data from GitHub API
    repository = requests.get(repository_url, headers=headers)
    # Convert the data obtained from GitHub API to JSON format
    repository = repository.json()

    # -------- DATA FOR FORECASTING --------
    # "pulls_url"
    pulls = repository_url + "/pulls?per_page=100"

    # "commits_url"
    commits = repository_url + "/commits?per_page=100"

    # "branches_url"
    branches = repository_url + "/branches?per_page=100"

    # "collaborators_url"
    collaborators = repository_url + "/collaborators?per_page=100"

    # "releases_url"
    releases = repository_url + "/releases?per_page=100"

    # --------------------------------------

    today = date.today()

    issues_reponse = []
    # Iterating to get issues for every month for the past 12 months
    for i in range(12):
        last_month = today + dateutil.relativedelta.relativedelta(months=-1)
        types = 'type:issue'
        repo = 'repo:' + repo_name
        ranges = 'created:' + str(last_month) + '..' + str(today)
        # By default GitHub API returns only 30 results per page
        # The maximum number of results per page is 100
        # For more info, visit https://docs.github.com/en/rest/reference/repos 
        per_page = 'per_page=100'
        # Search query will create a query to fetch data for a given repository in a given time range
        search_query = types + ' ' + repo + ' ' + ranges

        # Append the search query to the GitHub API URL 
        query_url = GITHUB_URL + "search/issues?q=" + search_query + "&" + per_page
        # requsets.get will fetch requested query_url from the GitHub API
        search_issues = requests.get(query_url, headers=headers, params=params)

        # -------- DATA FOR FORECASTING --------

        pull_data = requests.get(pulls)
        temp_text = pull_data.text
        pull_data = json.loads(temp_text)

        commit_data = requests.get(commits)
        temp_text = commit_data.text
        commit_data = json.loads(temp_text)

        branch_data = requests.get(branches)
        temp_text = branch_data.text
        branch_data = json.loads(temp_text)

        collaborator_data = requests.get(collaborators)
        temp_text = collaborator_data.text
        collaborator_data = json.loads(temp_text)

        release_data = requests.get(releases)
        temp_text = release_data.text
        release_data = json.loads(temp_text)

        # --------------------------------------

        # Convert the data obtained from GitHub API to JSON format
        search_issues = search_issues.json()
        issues_items = []
        try:
            # Extract "items" from search issues
            issues_items = search_issues.get("items")
        except KeyError:
            error = {"error": "Data Not Available"}
            resp = Response(json.dumps(error), mimetype='application/json')
            resp.status_code = 500
            return resp
        if issues_items is None:
            continue
        for issue in issues_items:
            label_name = []
            data = {}

            current_issue = issue
            # Get issue number
            data['issue_number'] = current_issue["number"]
            # Get created date of issue
            data['created_at'] = current_issue["created_at"][0:10]
            if current_issue["closed_at"] == None:
                data['closed_at'] = current_issue["closed_at"]
            else:
                # Get closed date of issue
                data['closed_at'] = current_issue["closed_at"][0:10]
            for label in current_issue["labels"]:
                # Get label name of issue
                label_name.append(label["name"])
            data['labels'] = label_name
            # It gives state of issue like closed or open
            data['State'] = current_issue["state"]
            # Get Author of issue
            data['Author'] = current_issue["user"]["login"]
            issues_reponse.append(data)

        # -------- DATA FOR FORECASTING --------

        pull_reponse = []
        commit_reponse = []
        branch_reponse = []
        collaborator_reponse = []
        release_reponse = []

        data_sets = [pull_data, commit_data, branch_data, collaborator_data, release_data]
        data_responses = [pull_reponse, commit_reponse, branch_reponse, collaborator_reponse, release_reponse]
        for i in range(len(data_sets)):
            data = {}
            x = data_sets[i]
            if x is None:
                continue
            else:
                for y in x:
                    data['pull_created_at'] = y['created_at'][0:10]
                data_responses[i].append(data)

        # --------------------------------------

        today = last_month

    df = pd.DataFrame(issues_reponse)

    # -------- DATA FOR FORECASTING --------

    df_pulls = pd.DataFrame(pull_reponse)
    df_commits = pd.DataFrame(commit_reponse)
    df_branches = pd.DataFrame(branch_reponse)
    df_collaborators = pd.DataFrame(collaborator_reponse)
    df_releases = pd.DataFrame(release_reponse)

    # --------------------------------------

    # Daily Created Issues
    df_created_at = df.groupby(['created_at'], as_index=False).count()
    dataFrameCreated = df_created_at[['created_at', 'issue_number']]
    dataFrameCreated.columns = ['date', 'count']

    '''
    Monthly Created Issues
    Format the data by grouping the data by month
    ''' 
    created_at = df['created_at']
    month_issue_created = pd.to_datetime(
        pd.Series(created_at), format='%Y/%m/%d')
    month_issue_created.index = month_issue_created.dt.to_period('m')
    month_issue_created = month_issue_created.groupby(level=0).size()
    month_issue_created = month_issue_created.reindex(pd.period_range(
        month_issue_created.index.min(), month_issue_created.index.max(), freq='m'), fill_value=0)
    month_issue_created_dict = month_issue_created.to_dict()
    created_at_issues = []
    for key in month_issue_created_dict.keys():
        array = [str(key), month_issue_created_dict[key]]
        created_at_issues.append(array)

    '''
    Monthly Closed Issues
    Format the data by grouping the data by WEEK
    ''' 
    
    closed_at = df['closed_at'].sort_values(ascending=True)
    month_issue_closed = pd.to_datetime(
        pd.Series(closed_at), format='%Y/%m/%d')
    month_issue_closed.index = month_issue_closed.dt.to_period('m')
    month_issue_closed = month_issue_closed.groupby(level=0).size()
    month_issue_closed = month_issue_closed.reindex(pd.period_range(
        month_issue_closed.index.min(), month_issue_closed.index.max(), freq='m'), fill_value=0)
    month_issue_closed_dict = month_issue_closed.to_dict()
    closed_at_issues = []
    for key in month_issue_closed_dict.keys():
        array = [str(key), month_issue_closed_dict[key]]
        closed_at_issues.append(array)



    # -------- DATA FOR FORECASTING --------

    # Pulls
    df_pulls = df_pulls.sort_values(ascending=True)
    pull_month = pd.to_datetime(
        pd.Series(df_pulls), format='%Y/%m/%d')
    pull_month.index = pull_month.dt.to_period('m')
    pull_month = pull_month.groupby(level=0).size()
    pull_month = pull_month.reindex(pd.period_range(
        pull_month.index.min(), pull_month.index.max(), freq='m'), fill_value=0)
    pull_month = pull_month.to_dict()
    p_data = []
    for key in pull_month.keys():
        array = [str(key), pull_month[key]]
        p_data.append(array)

    # Commits
    df_commits = df_commits.sort_values(ascending=True)
    commit_month = pd.to_datetime(
        pd.Series(df_commits), format='%Y/%m/%d')
    commit_month.index = commit_month.dt.to_period('m')
    commit_month = commit_month.groupby(level=0).size()
    commit_month = commit_month.reindex(pd.period_range(
        commit_month.index.min(), commit_month.index.max(), freq='m'), fill_value=0)
    commit_month = commit_month.to_dict()
    comm_data = []
    for key in commit_month.keys():
        array = [str(key), commit_month[key]]
        comm_data.append(array)

    # Branches
    df_branches = df_branches.sort_values(ascending=True)
    branch_month = pd.to_datetime(
        pd.Series(df_branches), format='%Y/%m/%d')
    branch_month.index = branch_month.dt.to_period('m')
    branch_month = branch_month.groupby(level=0).size()
    branch_month = branch_month.reindex(pd.period_range(
        branch_month.index.min(), branch_month.index.max(), freq='m'), fill_value=0)
    branch_month = branch_month.to_dict()
    b_data = []
    for key in branch_month.keys():
        array = [str(key), branch_month[key]]
        b_data.append(array)

    # Collaborators
    df_collaborators = df_collaborators.sort_values(ascending=True)
    collaborator_month = pd.to_datetime(
        pd.Series(df_collaborators), format='%Y/%m/%d')
    collaborator_month.index = collaborator_month.dt.to_period('m')
    collaborator_month = collaborator_month.groupby(level=0).size()
    collaborator_month = collaborator_month.reindex(pd.period_range(
        collaborator_month.index.min(), collaborator_month.index.max(), freq='m'), fill_value=0)
    collaborator_month = collaborator_month.to_dict()
    coll_data = []
    for key in collaborator_month.keys():
        array = [str(key), collaborator_month[key]]
        coll_data.append(array)

    # Releases
    df_releases = df_releases.sort_values(ascending=True)
    release_month = pd.to_datetime(
        pd.Series(df_releases), format='%Y/%m/%d')
    release_month.index = release_month.dt.to_period('m')
    release_month = release_month.groupby(level=0).size()
    release_month = release_month.reindex(pd.period_range(
        release_month.index.min(), release_month.index.max(), freq='m'), fill_value=0)
    release_month = release_month.to_dict()
    r_data = []
    for key in release_month.keys():
        array = [str(key), release_month[key]]
        r_data.append(array)

    # --------------------------------------

    '''
        1. Hit LSTM Microservice by passing issues_response as body
        2. LSTM Microservice will give a list of string containing image paths hosted on google cloud storage
        3. On recieving a valid response from LSTM Microservice, append the above json_response with the response from
            LSTM microservice
    '''
    created_at_body = {
        "issues": issues_reponse,
        "type": "created_at",
        "repo": repo_name.split("/")[1]
    }
    closed_at_body = {
        "issues": issues_reponse,
        "type": "closed_at",
        "repo": repo_name.split("/")[1]
    }

    # -------- DATA FOR FORECASTING --------

    pulls_body = {
        "issues": pull_reponse,
        "type": "pulls",
        "repo": repo_name.split("/")[1]
    }
    commits_body = {
        "issues": commit_reponse,
        "type": "commits",
        "repo": repo_name.split("/")[1]
    }
    branches_body = {
        "issues": branch_reponse,
        "type": "branches",
        "repo": repo_name.split("/")[1]
    }
    collaborators_body = {
        "issues": collaborator_reponse,
        "type": "collaborators",
        "repo": repo_name.split("/")[1]
    }
    releases_body = {
        "issues": release_reponse,
        "type": "releases",
        "repo": repo_name.split("/")[1]
    }

    # --------------------------------------

    # Update your Google cloud deployed LSTM app URL (NOTE: DO NOT REMOVE "/")
    LSTM_API_URL = "https://lstm-7fxxr4rxjq-uc.a.run.app/" + "api/forecast"

    '''
    Trigger the LSTM microservice to forecasted the created issues
    The request body consists of created issues obtained from GitHub API in JSON format
    The response body consists of Google cloud storage path of the images generated by LSTM microservice
    '''
    created_at_response = requests.post(LSTM_API_URL,
                                        json=created_at_body,
                                        headers={'content-type': 'application/json'})
    
    '''
    Trigger the LSTM microservice to forecasted the closed issues
    The request body consists of closed issues obtained from GitHub API in JSON format
    The response body consists of Google cloud storage path of the images generated by LSTM microservice
    '''    
    closed_at_response = requests.post(LSTM_API_URL,
                                       json=closed_at_body,
                                       headers={'content-type': 'application/json'})
    

    # -------- DATA FOR FORECASTING --------

    response_p = requests.post(LSTM_API_URL,
                                        json=pulls_body,
                                        headers={'content-type': 'application/json'})
    response_comm = requests.post(LSTM_API_URL,
                                        json=commits_body,
                                        headers={'content-type': 'application/json'})
    response_b = requests.post(LSTM_API_URL,
                                        json=branches_body,
                                        headers={'content-type': 'application/json'})
    response_coll = requests.post(LSTM_API_URL,
                                        json=collaborators_body,
                                        headers={'content-type': 'application/json'})
    response_r = requests.post(LSTM_API_URL,
                                        json=releases_body,
                                        headers={'content-type': 'application/json'})

    # --------------------------------------


    '''
    Create the final response that consists of:
        1. GitHub repository data obtained from GitHub API
        2. Google cloud image urls of created and closed issues obtained from LSTM microservice
    '''
    json_response = {
        "created": created_at_issues,
        "closed": closed_at_issues,
        "starCount": repository["stargazers_count"],
        "forkCount": repository["forks_count"],
        "createdAtImageUrls": {
            **created_at_response.json(),
        },
        "closedAtImageUrls": {
            **closed_at_response.json(),
        },
        "pullsImageUrls": {
            **response_p.json(),
        },
        "commitsImageUrls": {
            **response_comm.json(),
        },
        "branchesImageUrls": {
            **response_b.json(),
        },
        "collaboratorsImageUrls": {
            **response_coll.json(),
        },
        "releasesImageUrls": {
            **response_r.json(),
        },
    }
    # Return the response back to client (React app)
    return jsonify(json_response)


# Run flask app server on port 5000
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
