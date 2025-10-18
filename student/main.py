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
from dotenv import load_dotenv
load_dotenv()


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


# def get_sha_of_latest_commit(repo_name: str, branch: str="main"):
#     #Takes repo_name and branch name as argument and return the sha of latest commit on that branch using githuba api
#     # Correctly build the commits URL and return the top commit sha for the branch
#     url = f"https://api.github.com/repos/amolapratap/{repo_name}/commits/{branch}"
#     response = requests.get(url)
#     if response.status_code != 200:
#         raise Exception(f"Failed to get latest commit sha: {response.status_code}, {response.text}")
#     data = response.json()
#     # The commits endpoint returns a list; pick the first commit sha if present
#     if isinstance(data, list) and len(data) > 0:
#         return data[0].get("sha")
#     # Some endpoints may return an object with 'sha'
#     return data.get("sha")


def get_file_sha(repo_name: str, file_path: str):
    """
    Returns the SHA of a specific file in the repo (if it exists).
    This is needed when updating an existing file.
    """
    url = f"https://api.github.com/repos/amolapratap/{repo_name}/contents/{file_path}"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json().get("sha")
    return None



def push_files_to_repo(repo_name: str, files: list, round: int):
    # Takes a json array with object that have fields name of file and content of file and 
    # use GitHub API to push files to the repo
    
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

        # For round 2, get per-file SHA (if file exists)
        # file_sha = get_file_sha(repo_name, file_name) if round == 2 else None
        # if round == 2:
        file_sha = get_file_sha(repo_name, file_name)

        payload = {
            "message": f"Add {file_name}",
            "content": file_content
        }

        if file_sha:
            payload["sha"] = file_sha



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
        "input": [{"role": "user", "content": prompt}]
    }

    resp = requests.post(AIPIPE_URL, headers=headers, json=payload)
    if resp.status_code != 200:
        print(f"Error------------------------------{resp.status_code}: {resp.text}")
        resp.raise_for_status()

    try:
        data = resp.json()
        # ✅ New: handle both OpenAI and AIPipe schema variants
        if isinstance(data, dict):
            if "output" in data and data["output"]:
                # AIPipe new schema
                contents = data["output"][0].get("content", [])
                if contents and isinstance(contents, list):
                    return contents[0].get("text", "")
            elif "choices" in data and data["choices"]:
                # OpenAI-like schema
                return data["choices"][0]["message"]["content"]
    except Exception as e:
        print("Failed to extract content:", e)

    # if no clean text found, print full for debug
    print("⚠️ Unexpected AIPipe schema, returning raw text")
    print(resp.text[:400])
    return resp.text





def build_prompt_for_task(task_json: dict):

    task_name = task_json.get("task", "Unnamed Task")
    brief = task_json.get("brief", "No brief provided.")
    evaluation_url = task_json.get("evaluation_url", "")
    attachments = task_json.get("attachments", [])
    checks = task_json.get("checks", [])

    # Build readable attachment section
    attachment_text = "\n".join(
        [f"- {a['name']}: {a['url']}" for a in attachments]
    ) if attachments else "No attachments provided."

    # Build readable checks section
    checks_text = "\n".join(
        [f"- {c}" for c in checks]
    ) if checks else "No specific checks mentioned."

    # ------------------- Construct full prompt -------------------
    prompt = f"""
        You are an expert AI coding assistant.
        Your goal is to complete the following **task**:

        🧩 **Task Name:** {task_name}

        📋 **Brief:**  
        {brief}

        📎 **Attachments:**  
        {attachment_text}

        ✅ **Checks / Evaluation Criteria:**  
        {checks_text}

        🔗 **Evaluation Callback URL:** {evaluation_url or 'N/A'}

        ---

        ### Output Format

        You must output a **complete code project** as a JSON array of files.
        Each file must be an object in this format:
        Follow exact as given

        ```json
        [
        {{"name": "index.html", "content": "<!doctype html>..."}},
        {{"name": "README.md", "content": "# Project Description ..."}},
        {{ "name": "LICENSE", "content": "MIT License text ..." }}
        ]

        """
    return prompt




def write_code_with_llm(task_json: dict):
    prompt = build_prompt_for_task(task_json)
    print("prompt--------------------------------------------",type(prompt),prompt)
    raw = call_aipipe(prompt)

    print("🔍 RAW AIPipe OUTPUT PREVIEW (first 400 chars):")
    print(raw[:400])
    print("------------------------------------------------")

    # Try to extract ```json ... ```
    match = re.search(r"```json\s*(.*?)\s*```", raw, re.DOTALL)
    json_text = match.group(1) if match else raw.strip()

    try:
        files = json.loads(json_text)
        if isinstance(files, list):
            print("✅ Parsed valid JSON list of files.")
            return files
        else:
            raise ValueError("Parsed JSON is not a list")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Invalid JSON output from AIPipe: {e}\n\nRaw snippet:\n{raw[:400]}")



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
    create_github_repo(f"{data["task"]}_{data["nonce"]}")
    # enable_github_pages(f"{data["task"]}_{data["nonce"]}")
    push_files_to_repo(f"{data["task"]}_{data["nonce"]}", files, 1)
    enable_github_pages(f"{data["task"]}_{data["nonce"]}")



def get_repo_files(repo_name: str):
    url = f"https://api.github.com/repos/amolapratap/{repo_name}/contents"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }
    resp = requests.get(url, headers=headers)
    if resp.status_code != 200:
        raise Exception(f"Failed to list repo files: {resp.status_code}, {resp.text}")
    
    files = []
    for item in resp.json():
        if item["type"] == "file":
            # get raw content
            raw = requests.get(item["download_url"]).text
            files.append({"name": item["name"], "content": raw})
    return files




def round2(data):
    repo_name = f"{data['task']}_{data['nonce']}"
    existing_files = get_repo_files(repo_name)

    # Build a prompt for "refactor/improve" mode
    prompt = f"""
    You are an expert AI developer.

    Task Name: {data.get('task')}
    Round: 2 (Refinement / Enhancement)
    Brief: {data.get('brief')}

    The repository currently contains the following files:
    {json.dumps([f['name'] for f in existing_files], indent=2)}

    Below are their contents (truncated if large):
    ---
    {textwrap.shorten(json.dumps(existing_files, indent=2), width=2000, placeholder="...")}
    ---

    Now, **improve or refactor** the code according to new or existing checks:
    {data.get('checks', [])}

    Output the full updated project again as a JSON array of files:
    ```json
    [
      {{"name": "index.html", "content": "..."}},
      {{"name": "README.md", "content": "..."}},
      ...
    ]
    ```
    """

    raw = call_aipipe(prompt)
    match = re.search(r"```json\s*(.*?)\s*```", raw, re.DOTALL)
    json_text = match.group(1) if match else raw.strip()

    try:
        files = json.loads(json_text)
        if not isinstance(files, list):
            raise ValueError("Parsed JSON is not a list")
        push_files_to_repo(repo_name, files, 2)
        print(f"✅ Round 2: Repo {repo_name} updated successfully.")
        return {"message": "Round 2 completed successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Invalid JSON output from AIPipe: {e}\n\nRaw snippet:\n{raw[:400]}")



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
    uvicorn.run(app, host="0.0.0.0", port=7860)
    # uvicorn.run(app, host="0.0.0.0", port=8000)


