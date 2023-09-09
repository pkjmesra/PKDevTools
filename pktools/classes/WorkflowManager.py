"""
    The MIT License (MIT)

    Copyright (c) 2023 pkjmesra

    Permission is hereby granted, free of charge, to any person obtaining a copy
    of this software and associated documentation files (the "Software"), to deal
    in the Software without restriction, including without limitation the rights
    to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
    copies of the Software, and to permit persons to whom the Software is
    furnished to do so, subject to the following conditions:

    The above copyright notice and this permission notice shall be included in all
    copies or substantial portions of the Software.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
    AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
    OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
    SOFTWARE.

"""
from pktools.classes.Fetcher import fetcher
from pktools.classes.Telegram import get_secrets

def run_workflow(command,user,options,workflow_name,branch, owner, repo):
    _,_,_,ghp_token = get_secrets()
    url = f"https://api.github.com/repos/{owner}/{repo}/actions/workflows/{workflow_name}/dispatches"
    
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {ghp_token}",
        "Content-Type": "application/json"
    }
    data = '{"ref":"'+branch+'","inputs":{"user":"'+f'{user}'+'","params":"'+f'{options}'+'","name":"'+f'{command}'+'"}}'
    resp = fetcher.postURL(url, data=data, headers=headers)
    if resp.status_code==204:
        print(f"Workflow {workflow_name} Triggered for command:{command} for user:{user} with options:{options}!")
    else:
        print(f"Something went wrong while triggering {workflow_name} for command:{command} for user:{user} with options:{options}")
    return resp

# resp = run_workflow("B_12_1","-1001785195297")