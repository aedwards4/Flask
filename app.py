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

today = date.today()
'''
API route path is  "/api/forecast"
This API will accept only POST request
'''
@app.route('/api/github', methods=['POST'])
def github():
    global today

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

    # today = date.today()

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

        today = last_month

    # -------- DATA FOR FORECASTING --------

    pull_data = requests.get(pulls, headers=headers)
    temp_text = pull_data.text
    pull_data = json.loads(temp_text)

    commit_data = requests.get(commits, headers=headers)
    temp_text = commit_data.text
    commit_data = json.loads(temp_text)

    branch_data = requests.get(branches, headers=headers)
    temp_text = branch_data.text
    branch_data = json.loads(temp_text)

    collaborator_data = requests.get(collaborators, headers=headers)
    temp_text = collaborator_data.text
    collaborator_data = json.loads(temp_text)

    release_data = requests.get(releases, headers=headers)
    temp_text = release_data.text
    release_data = json.loads(temp_text)

    pull_reponse = []
    commit_reponse = []
    branch_reponse = []
    collaborator_reponse = []
    release_reponse = []

    data_sets = [pull_data, commit_data, branch_data, collaborator_data, release_data]
    data_responses = [pull_reponse, commit_reponse, branch_reponse, collaborator_reponse, release_reponse]

    coll_sets = {}
    for i in range(len(data_sets)):
        
        dset = data_sets[i]
        if dset is None:
            continue
        else:
            for item in dset:
                data = {}
                if i == 0: # pulls - DONE
                    data['pull_created_at'] = item['created_at'][0:10]
                elif i == 1: # commits - DONE
                    commit_url = requests.get(item['url'], headers=headers)
                    temp_text = commit_url.text
                    commit = json.loads(temp_text)
                    print(commit)
                    data['commit_created_at'] = commit['commit']['author']['date'][0:10]
                elif i == 2: # branches - DONE
                    commit_url = requests.get(item['commit']['url'], headers=headers)
                    temp_text = commit_url.text
                    commit = json.loads(temp_text)
                    data['branch_created_at'] = commit['commit']['author']['date'][0:10]
                elif i == 3:
                    for commit in commit_data:
                        commit_url = requests.get(commit['url']+"?per_page=400", headers=headers)
                        temp_text = commit_url.text
                        commit = json.loads(temp_text)
                        date = commit['commit']['author']['date'][0:10]
                        print(date)
                        month = date[:7]
                        contributor = commit['commit']['author']['email']

                        if month in coll_sets.keys():
                            if contributor not in coll_sets[month]:
                                coll_sets[month].add(contributor)
                                collaborator_reponse.append({'collab_created_at':date})
                        else:
                            coll_sets[month] = {contributor}
                            collaborator_reponse.append({'collab_created_at':date})
                elif i == 4: # releases - DONE
                    data['release_created_at'] = item['created_at'][0:10]

                if i != 3:
                    data_responses[i].append(data)

    # --------------------------------------

    df = pd.DataFrame(issues_reponse)

    # Daily Created Issues
    df_created_at = df.groupby(['created_at'], as_index=False).count()
    df_closed_at = df.groupby(['closed_at'], as_index=False).count()

    dataFrameCreated = df_created_at[['created_at', 'issue_number']]
    dataFrameClosed = df_closed_at[['closed_at', 'issue_number']]

    dataFrameCreated.columns = ['date', 'count']
    dataFrameClosed.columns = ['date', 'count']


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

    maxClosed = 0
    month = ""
    for data2 in closed_at_issues:
        if data2[1] > maxClosed:
            maxClosed = data2[1]
            month = data2[0][-2:]

    days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
    months = {'01':'january', '02':'february', '03':'march', '04':'april', '05':'may', '06':'june',
            '07':'july', '08':'august', '09':'september', '10':'october', '11':'november', '12':'december'}

    month_max_issues_closed = months[month]

    '''
    Day of Week with Max closed issues
    ''' 
    daily_closed_at = df['closed_at']
    day_issue_closed = pd.to_datetime(
        pd.Series(daily_closed_at), format='%Y/%m/%d')
    day_issue_closed.index = day_issue_closed.dt.to_period('d')
    day_issue_closed = day_issue_closed.groupby(level=0).size()
    day_issue_closed = day_issue_closed.reindex(pd.period_range(
        day_issue_closed.index.min(), day_issue_closed.index.max(), freq='d'), fill_value=0)
    day_issue_closed_dict = day_issue_closed.to_dict()
    weekday_closed_at = []
    for key in day_issue_closed_dict.keys():
        temp_day = key.to_timestamp().weekday()
        temp_dict = {"daily_closed_at": temp_day, "num_issues": day_issue_closed_dict[key]}
        weekday_closed_at.append(temp_dict)

    data_frame = pd.DataFrame(weekday_closed_at)
    df2 = data_frame.groupby("daily_closed_at", as_index=False).sum()
    weekday_sums = df2.to_dict()
    max_issues = 0 
    weekday = -1
    for key in weekday_sums['num_issues'].keys():
        if weekday_sums['num_issues'][key] > max_issues:
            max_issues = weekday_sums['num_issues'][key]
            weekday = key

    
    day_max_issues_closed = days[weekday]

    '''
    Day of Week with Max created issues
    ''' 
    daily_created_at = df['created_at']
    day_issue_created = pd.to_datetime(
        pd.Series(daily_created_at), format='%Y/%m/%d')
    day_issue_created.index = day_issue_created.dt.to_period('d')
    day_issue_created = day_issue_created.groupby(level=0).size()
    day_issue_created = day_issue_created.reindex(pd.period_range(
        day_issue_created.index.min(), day_issue_created.index.max(), freq='d'), fill_value=0)
    day_issue_created_dict = day_issue_created.to_dict()
    weekday_created_at = []
    for key in day_issue_created_dict.keys():
        # temp_date = key.to_timestamp().to_pydatetime()
        temp_day = key.to_timestamp().weekday()
        temp_dict = {"daily_created_at": temp_day, "num_issues": day_issue_created_dict[key]}
        weekday_created_at.append(temp_dict)

    data_frame = pd.DataFrame(weekday_created_at)
    df2 = data_frame.groupby("daily_created_at", as_index=False).sum()
    weekday_sums = df2.to_dict()
    max_issues = 0 
    weekday = -1
    for key in weekday_sums['num_issues'].keys():
        if weekday_sums['num_issues'][key] > max_issues:
            max_issues = weekday_sums['num_issues'][key]
            weekday = key

    days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
    day_max_issues_created = days[weekday]
    print(day_max_issues_created)

    # -------- DATA FOR FORECASTING --------

    '''
    Monthly Pulls
    Format the data by grouping the data by month
    ''' 

    df_pulls = pd.DataFrame(pull_reponse)
    df_pulls.rename(columns={'pull_created_at':'ds'}, inplace=True)
    df_pulls['y'] = 1
    df_pulls = df_pulls.sort_values(by=['ds'],ascending=True)
    pull_month = pd.to_datetime(
    pd.Series(df_pulls['ds']), format='%Y/%m/%d')
    pull_month.index = pull_month.dt.to_period('m')
    pull_month = pull_month.groupby(level=0).size()
    pull_month = pull_month.reindex(pd.period_range(
        pull_month.index.min(), pull_month.index.max(), freq='m'), fill_value=0)
    pull_month = pull_month.to_dict()
    p_data = []
    for key in pull_month.keys():
        array = [str(key), pull_month[key]]
        p_data.append(array)
    df_pulls = pd.DataFrame(p_data)
    df_pulls.rename(columns={0:'ds', 1:'y'}, inplace=True)   

    
    '''
    Monthly Commits
    Format the data by grouping the data by month
    ''' 
    df_commits = pd.DataFrame(commit_reponse)
    df_commits.rename(columns={'commit_created_at':'ds'}, inplace=True)
    df_commits['y'] = 1
    df_commits = df_commits.sort_values(by=['ds'],ascending=True)
    commit_month = pd.to_datetime(
    pd.Series(df_commits['ds']), format='%Y/%m/%d')
    commit_month.index = commit_month.dt.to_period('m')
    commit_month = commit_month.groupby(level=0).size()
    commit_month = commit_month.reindex(pd.period_range(
        commit_month.index.min(), commit_month.index.max(), freq='m'), fill_value=0)
    commit_month = commit_month.to_dict()
    comm_data = []
    for key in commit_month.keys():
        array = [str(key), commit_month[key]]
        comm_data.append(array)
    df_commits = pd.DataFrame(comm_data)
    df_commits.rename(columns={0:'ds', 1:'y'}, inplace=True) 

    
    '''
    Monthly Branches
    Format the data by grouping the data by month
    ''' 
    df_branches = pd.DataFrame(branch_reponse)
    df_branches.rename(columns={'branch_created_at':'ds'}, inplace=True)
    df_branches['y'] = 1
    df_branches = df_branches.sort_values(by=['ds'],ascending=True)
    branch_month = pd.to_datetime(
    pd.Series(df_branches['ds']), format='%Y/%m/%d')
    branch_month.index = branch_month.dt.to_period('m')
    branch_month = branch_month.groupby(level=0).size()
    branch_month = branch_month.reindex(pd.period_range(
        branch_month.index.min(), branch_month.index.max(), freq='m'), fill_value=0)
    branch_month = branch_month.to_dict()
    b_data = []
    for key in branch_month.keys():
        array = [str(key), branch_month[key]]
        b_data.append(array)
    df_branches = pd.DataFrame(b_data)
    df_branches.rename(columns={0:'ds', 1:'y'}, inplace=True) 

    
    '''
    Monthly Collaborators
    Format the data by grouping the data by month
    ''' 
    df_collab = pd.DataFrame(collaborator_reponse)
    df_collab.rename(columns={'collab_created_at':'ds'}, inplace=True)
    df_collab['y'] = 1
    df_collab = df_collab.sort_values(by=['ds'],ascending=True)
    collab_month = pd.to_datetime(
    pd.Series(df_collab['ds']), format='%Y/%m/%d')
    collab_month.index = collab_month.dt.to_period('m')
    collab_month = collab_month.groupby(level=0).size()
    collab_month = collab_month.reindex(pd.period_range(
        collab_month.index.min(), collab_month.index.max(), freq='m'), fill_value=0)
    collab_month = collab_month.to_dict()
    b_data = []
    for key in collab_month.keys():
        array = [str(key), collab_month[key]]
        b_data.append(array)
    df_collab = pd.DataFrame(b_data)
    df_collab.rename(columns={0:'ds', 1:'y'}, inplace=True) 

    
    '''
    Monthly Releases
    Format the data by grouping the data by month
    ''' 
    df_releases = pd.DataFrame(release_reponse)
    df_releases.rename(columns={'release_created_at':'ds'}, inplace=True)
    df_releases['y'] = 1
    df_releases = df_releases.sort_values(by=['ds'],ascending=True)
    rel_month = pd.to_datetime(
    pd.Series(df_releases['ds']), format='%Y/%m/%d')
    rel_month.index = rel_month.dt.to_period('m')
    rel_month = rel_month.groupby(level=0).size()
    rel_month = rel_month.reindex(pd.period_range(
        rel_month.index.min(), rel_month.index.max(), freq='m'), fill_value=0)
    rel_month = rel_month.to_dict()
    r_data = []
    for key in rel_month.keys():
        array = [str(key), rel_month[key]]
        r_data.append(array)
    df_releases = pd.DataFrame(r_data)
    df_releases.rename(columns={0:'ds', 1:'y'}, inplace=True) 


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

    # daily_created_at_body = {
    #     "issues": weekday_created_at,
    #     "type": "daily_created_at",
    #     "repo": repo_name.split("/")[1]
    # }

    # daily_closed_at_body = {
    #     "issues": weekday_closed_at,
    #     "type": "daily_closed_at",
    #     "repo": repo_name.split("/")[1]
    # }

    pulls_body = {
        "issues": pull_reponse,
        "type": "pull_created_at",
        "repo": repo_name.split("/")[1]
    }
    commits_body = {
        "issues": commit_reponse,
        "type": "commit_created_at",
        "repo": repo_name.split("/")[1]
    }
    branches_body = {
        "issues": branch_reponse,
        "type": "branch_created_at",
        "repo": repo_name.split("/")[1]
    }
    collaborators_body = {
        "issues": collaborator_reponse,
        "type": "collab_created_at",
        "repo": repo_name.split("/")[1]
    }
    releases_body = {
        "issues": release_reponse,
        "type": "release_created_at",
        "repo": repo_name.split("/")[1]
    }

    # --------------------------------------

    # Update your Google cloud deployed LSTM app URL (NOTE: DO NOT REMOVE "/")
    LSTM_API_URL = "https://lstm-7fxxr4rxjq-uc.a.run.app/" + "api/forecast"
    FBPROPHET_API_URL = "https://fbprophet-bdqju5ggxa-uc.a.run.app/" + "api/forecast"

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

    # response_daily_created_at = requests.post(LSTM_API_URL,
    #                                     json=daily_created_at_body,
    #                                     headers={'content-type': 'application/json'})
    # response_daily_closed_at = requests.post(LSTM_API_URL,
    #                                     json=daily_closed_at_body,
    #                                     headers={'content-type': 'application/json'})
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

    # -------- FB/PROPHET --------
    FBPROPHET_API_URL = "https://fbprophet-bdqju5ggxa-uc.a.run.app/" + "api/forecast"

    fb_created_at = requests.post(FBPROPHET_API_URL,
                                        json=created_at_body,
                                        headers={'content-type': 'application/json'})

    fb_closed_at = requests.post(FBPROPHET_API_URL,
                                       json=closed_at_body,
                                       headers={'content-type': 'application/json'})
    # fb_daily_created_at = requests.post(FBPROPHET_API_URL,
    #                                     json=daily_created_at_body,
    #                                     headers={'content-type': 'application/json'})
    # fb_daily_closed_at = requests.post(FBPROPHET_API_URL,
    #                                     json=daily_closed_at_body,
    #                                     headers={'content-type': 'application/json'})
    fb_pulls= requests.post(FBPROPHET_API_URL,
                                        json=pulls_body,
                                        headers={'content-type': 'application/json'})
    fb_commits = requests.post(FBPROPHET_API_URL,
                                        json=commits_body,
                                        headers={'content-type': 'application/json'})
    fb_branches = requests.post(FBPROPHET_API_URL,
                                        json=branches_body,
                                        headers={'content-type': 'application/json'})
    fb_collabs = requests.post(FBPROPHET_API_URL,
                                        json=collaborators_body,
                                        headers={'content-type': 'application/json'})
    fb_releases = requests.post(FBPROPHET_API_URL,
                                        json=releases_body,
                                        headers={'content-type': 'application/json'})
     # --------------------------------------

     # -------- STATS-MODELS --------
    STATSMODELS_API_URL = "https://stats-models-xk57uhjxlq-uc.a.run.app/" + "api/forecast"

    sm_created_at = requests.post(STATSMODELS_API_URL,
                                        json=created_at_body,
                                        headers={'content-type': 'application/json'})

    sm_closed_at = requests.post(STATSMODELS_API_URL,
                                       json=closed_at_body,
                                       headers={'content-type': 'application/json'})
    # sm_daily_created_at = requests.post(STATSMODELS_API_URL,
    #                                     json=created_at_body,
    #                                     headers={'content-type': 'application/json'})
    # sm_daily_closed_at = requests.post(STATSMODELS_API_URL,
    #                                    json=closed_at_body,
    #                                    headers={'content-type': 'application/json'})
    sm_pulls= requests.post(STATSMODELS_API_URL,
                                        json=pulls_body,
                                        headers={'content-type': 'application/json'})
    sm_commits = requests.post(STATSMODELS_API_URL,
                                        json=commits_body,
                                        headers={'content-type': 'application/json'})
    sm_branches = requests.post(STATSMODELS_API_URL,
                                        json=branches_body,
                                        headers={'content-type': 'application/json'})
    sm_collabs = requests.post(STATSMODELS_API_URL,
                                        json=collaborators_body,
                                        headers={'content-type': 'application/json'})
    sm_releases = requests.post(STATSMODELS_API_URL,
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
        "dailyCreatedMax": day_max_issues_created,
        "dailyClosedMax": day_max_issues_closed,
        "monthlyClosedMax": month_max_issues_closed,
        "createdAtImageUrls": {
            "LSTM": {
                **created_at_response.json(),
            },
            "FB": {
                **fb_created_at.json(),
            },
            "SM": {
                **sm_created_at.json(),
            },
        },
        "closedAtImageUrls": {
            "LSTM": {
                **closed_at_response.json(),
            },
            "FB": {
                **fb_closed_at.json(),
            },
            "SM": {
                **sm_closed_at.json(),
            },
        },
        "pullsImageUrls": {
            "LSTM": {
                **response_p.json(),
            },
            "FB": {
                **fb_pulls.json(),
            },
            "SM": {
                **sm_pulls.json(),
            },
        },
        "commitsImageUrls": {
            "LSTM": {
                **response_comm.json(),
            },
            "FB": {
                **fb_commits.json(),
            },
            "SM": {
                **sm_commits.json(),
            },
        },
        "branchesImageUrls": {
            "LSTM": {
                **response_b.json(),
            },
            "FB": {
                **fb_branches.json(),
            },
            "SM": {
                **sm_branches.json(),
            },
        },
        "collaboratorsImageUrls": {
            "LSTM": {
                **response_coll.json(),
            },
            "FB": {
                **fb_collabs.json(),
            },
            "SM": {
                **sm_collabs.json(),
            },
        },
        "releasesImageUrls": {
            "LSTM": {
                **response_r.json(),
            },
            "FB": {
                **fb_releases.json(),
            },
            "SM": {
                **sm_releases.json(),
            },
        },
    }
    # Return the response back to client (React app)
    return jsonify(json_response)


# Run flask app server on port 5000
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
