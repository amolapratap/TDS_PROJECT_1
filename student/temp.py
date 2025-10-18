# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "fastapi[standard]",
#   "unicorn",
#   "requests"
# ]
# ///

import re
import requests
import os
import base64
import json
import textwrap
from  fastapi import FastAPI, HTTPException

GITHUB_TOKEN=os.getenv("GITHUB_TOKEN")

#AIPIPE_URL = "https://aipipe.org/api/v1/generate"
AIPIPE_URL = "https://aipipe.org/openai/v1/responses"
AIPIPE_API_KEY = os.getenv("AIPIPE_API_KEY") 

app = FastAPI()

#Chek secret key
def validate_secret(secret: str):
    return secret ==  os.getenv("secret")


def create_github_repo(repo_name: str):
    # use gitbub api to create a repo with given name
    payload={
        "name": repo_name,
        "private": False,
        "auto_init": True,
        "license_template": "mit"
    }

    #Setting to application/vnd.github+json is recommended.
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }

    response = requests.post(
        "https://api.github.com/user/repos",
        headers=headers,
        json=payload
    )

    if response.status_code != 201:
        raise Exception(f"Failed to create repo: {response.status_code},{response.text}")
    else:
        return response.json()


def enable_github_pages(repo_name: str):    #Deploy
    #Takes repo name as argument and enables github pages for that repo using the GitHub API
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }       

    payload = {
        "build_type": "legacy",
        "source": {
            "branch": "main",
            "path": "/"
        }
    }
    response = requests.post(
        f"https://api.github.com/repos/amolapratap/{repo_name}/pages",
        headers=headers,
        json=payload
    )

    if response.status_code != 201:
        raise Exception(f"Failed to enable GitHub Pages: {response.status_code}, {response.text}")
    else:
        return response.json()


def get_sha_of_latest_commit(repo_name: str, branch: str="main"):
    #Takes repo_name and branch name as argument and return the sha of latest commit on that branch using githuba api
    # Correctly build the commits URL and return the top commit sha for the branch
    url = f"https://api.github.com/repos/amolapratap/{repo_name}/commits/{branch}"
    response = requests.get(url)
    if response.status_code != 200:
        raise Exception(f"Failed to get latest commit sha: {response.status_code}, {response.text}")
    data = response.json()
    # The commits endpoint returns a list; pick the first commit sha if present
    if isinstance(data, list) and len(data) > 0:
        return data[0].get("sha")
    # Some endpoints may return an object with 'sha'
    return data.get("sha")


def push_files_to_repo(repo_name: str, files: list, round: int):
    # Takes a json array with object that have fields name of file and content of file and 
    # use GitHub API to push files to the repo

    if round == 2:
        latest_sha = get_sha_of_latest_commit(repo_name)
    else:
        latest_sha = None
    
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }

    for file in files:
        file_name = file.get("name")
        file_content = file.get("content")  
        #If content is bytes, convert it base64 string
        if isinstance(file_content, bytes):
            file_content = base64.b64encode(file_content).decode("utf-8")
        else:
            #if content is a string, still encode to base64
            file_content = base64.b64encode(file_content.encode("utf-8")).decode("utf-8")
        payload = {
            "message": f"Add {file_name}",
            "content": file_content
        }
        if latest_sha:
            payload["sha"] = latest_sha

        # Create a commit for each file in repo
        response = requests.put(
            f"https://api.github.com/repos/amolapratap/{repo_name}/contents/{file_name}",
            headers=headers,
            json=payload,
            timeout=30,
        )

        # GitHub returns 201 for created, 200 for updated
        if response.status_code not in (200, 201):
            # include response snippet to help debugging
            raise Exception(
                f"Failed to push file {file_name}: {response.status_code}, {response.text[:1000]}"
            )
        else:
            print(f"File {file_name} pushed successfully to {repo_name} (status={response.status_code})")




def call_aipipe(prompt: str, max_tokens: int = 2000) -> str:
    headers = {
        "Authorization": f"Bearer {AIPIPE_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "gpt-4o-mini",
        # "prompt": prompt,
        "input": prompt,
    }

    resp = requests.post(AIPIPE_URL, headers=headers, json=payload)
    if resp.status_code != 200:
        print(f"Error------------------------------{resp.status_code}: {resp.text}")
    resp.raise_for_status()
    data = resp.json()
    # if "text" in data:
    if "response" in data:
        # return data["text"]
        return data["response"]
    elif "choices" in data and len(data["choices"]) > 0:
        return data["choices"][0].get("text", "")
    return json.dumps(data)




def build_prompt_for_task(task_json: dict) -> str:
    brief = task_json.get("brief", "")
    checks = task_json.get("checks", [])
    nonce = task_json.get("nonce", "")
    prompt = f"""
    You are an expert frontend developer.
    Create a small SINGLE PAGE app (index.html + README.md + LICENSE).
    The page must:
    - Display an image passed as ?url= parameter
    - Auto-solve a captcha demo within 15 seconds (show 'Solved text' field updated automatically)
    - Include nonce {nonce} visibly on page footer
    - Be responsive and professional

    Include also a professional README.md and MIT License.
    Output STRICT JSON array:
    [
      {{ "name": "index.html", "content": "<html>...</html>" }},
      {{ "name": "README.md", "content": "# ..." }},
      {{ "name": "LICENSE", "content": "MIT License text ..." }}
    ]
    """
    return prompt



import re
import json
from fastapi import HTTPException

def write_code_with_llm(task_json: dict):
    prompt = build_prompt_for_task(task_json)
    raw = call_aipipe(prompt)

    # If AIPipe returned a structured JSON response, extract inner text
    try:
        resp = json.loads(raw)
        if (
            isinstance(resp, dict)
            and "output" in resp
            and isinstance(resp["output"], list)
            and len(resp["output"]) > 0
            and "content" in resp["output"][0]
        ):
            content_list = resp["output"][0]["content"]
            if content_list and "text" in content_list[0]:
                raw = content_list[0]["text"]
    except json.JSONDecodeError:
        # raw wasn't a JSON string — fine, move on
        pass

    # Now extract JSON inside ```json ... ```
    match = re.search(r"```json\s*(.*?)\s*```", raw, re.DOTALL)
    json_text = match.group(1) if match else raw.strip()

    try:
        files = json.loads(json_text)
        if isinstance(files, list):
            return files
        else:
            raise ValueError("Parsed JSON is not a list")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Invalid JSON output from AIPipe: {e}")



# def write_code_with_llm(task_json: dict):
#     prompt = build_prompt_for_task(task_json)
#     raw = call_aipipe(prompt)

#     print("---------------------- RAW AIPipe OUTPUT START ----")
#     print(raw)
#     print("---------------------- RAW AIPipe OUTPUT END ----")


#     try:
#         # If AIPipe returns a string (most likely)
#         if isinstance(raw, str):
#             files = json.loads(raw)
#         # If it already returns JSON/dict
#         elif isinstance(raw, dict):
#             content = raw.get("output", [{}])[0].get("content", "")
#             files = json.loads(content) if isinstance(content, str) else content
#         else:
#             raise HTTPException(status_code=500, detail="Unexpected type from AIPipe response")

#         if isinstance(files, list):
#             return files
#         else:
#             raise HTTPException(status_code=500, detail="Unexpected response format from AIPipe")

#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Invalid JSON output from AIPipe: {e}")

    # try:
    #     files = json.loads(raw)
    #     if isinstance(files, list):
    #         return files
    # except Exception:
    #     raise HTTPException(status_code=500, detail="Invalid JSON output from AIPipe")
    # return []


# def write_code_with_llm():
#     #Hardcode with a single file for now
#     #TODO : integrate with llm to generate code

#     return [
#         {
#             "name": "index.html",
#             "content": """
#                     <!doctype html>
#                     <html lang="en">
#                     <head>
#                     <meta charset="utf-8" />
#                     <meta name="viewport" content="width=device-width,initial-scale=1" />
#                     <title>Hello India</title>
#                     <style>
#                         html,body {
#                         height: 100%;
#                         margin: 0;
#                         font-family: Inter, system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial;
#                         display: grid;
#                         place-items: center;
#                         background: linear-gradient(135deg,#fef3c7,#fde68a);
#                         color: #0f172a;
#                         }
#                         .card {
#                         padding: 2.25rem 2.5rem;
#                         border-radius: 16px;
#                         box-shadow: 0 8px 30px rgba(2,6,23,0.12);
#                         text-align: center;
#                         transform: translateY(0);
#                         }
#                         h1 { font-size: 2.25rem; margin: 0 0 .5rem; }
#                         p { margin: 0; color: #334155; }
#                         .pulse {
#                         display:inline-block;
#                         margin-left: .6rem;
#                         width: .9rem; height: .9rem;
#                         background: #ef4444;
#                         border-radius: 999px;
#                         box-shadow: 0 0 0 rgba(239,68,68,0.6);
#                         animation: pulse 1.6s infinite;
#                         vertical-align: middle;
#                         }
#                         @keyframes pulse {
#                         0% { box-shadow: 0 0 0 0 rgba(239,68,68,0.6); transform: scale(.95); }
#                         70% { box-shadow: 0 0 0 12px rgba(239,68,68,0); transform: scale(1.06); }
#                         100% { box-shadow: 0 0 0 0 rgba(239,68,68,0); transform: scale(.95); }
#                         }
#                     </style>
#                     </head>
#                     <body>
#                     <div class="card">
#                         <h1>Hello India, OCT 2025<span class="pulse" aria-hidden="true"></span></h1>
#                         <p>Deployed with GitHub Pages — test successful ✅</p>
#                     </div>
#                     </body>
#                     </html>
#                     """
#         }

#     ]



def round1(data):
    files = write_code_with_llm(data)
    #create_github_repo(f"{data["task"]}_{data["nonce"]}")
    #enable_github_pages(f"{data["task"]}_{data["nonce"]}")
    push_files_to_repo(f"{data["task"]}_{data["nonce"]}", files, 1)



def round2(data):
    pass


# Post End point that takes a json object with following fields: Eamil, secret, task, round, nounce, brief, checksum, brief, checks(array), evaluation_url, attachments(array with object with fields name and url)
@app.post("/handle_task")
def handle_task(data: dict):
    # Process the task here
    # You can access the fields like task['Email'], task['secret'], etc

    if not validate_secret(data.get("secret", "")):
        return {"error": "Invalid Secret"}
    else:
        # Process Task
        #print(data.get("round"))
        if data.get("round")==1:
            round1(data)
            print(data)
            return {"message": "Round 1 Started"}
        elif data.get("round") ==2:
            round2(data)
            return {"message": "Round 2 Started"}
        else:
            return{"error": "Invalid round"}
    print(data)

    return {"status": "success", "message": "Task processed successfully", "data": data}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)





##Promptdef build_prompt_for_task(task_json: dict) -> str:
    brief = task_json.get("brief", "")
    nonce = task_json.get("nonce", "")

    prompt = f"""
You are a code generator API. Your ONLY task is to output **strict JSON**, no explanations or markdown.

Task:
Create a small SINGLE PAGE web app with:
- index.html (shows ?url= image, solves captcha within 15s, displays nonce {nonce} visibly in footer)
- README.md (short professional readme)
- LICENSE (MIT license text)

Output format EXACTLY:
[
  {{ "name": "index.html", "content": "<!DOCTYPE html>...</html>" }},
  {{ "name": "README.md", "content": "# ..." }},
  {{ "name": "LICENSE", "content": "MIT License text ..." }}
]
"""
    return prompt.strip()