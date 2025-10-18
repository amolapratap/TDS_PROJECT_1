# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "requests",
# ]
# ///

import requests

# def send_task():
#     payload = {
#         "email": "student@example.com",
#         "secret": "amazing1",
#         "task": "captcha-solver-...",
#         "round": 2,
#         "nonce": "ab12-...",
#         #"brief": "Create a captcha solver that handles ?url=https://.../image.png. Default to attached sample.",
#         "brief": "Create a captcha solver that handles ?url=https://c22blog.wordpress.com/wp-content/uploads/2010/10/input-black.gif. Default to attached sample.",
#         "checks": [
#             "Repo has MIT license",
#             "README.md is professional",
#             # "Page displays captcha URL passed at ?url=...",
#             "Page displays captcha URL passed at ?url=https://c22blog.wordpress.com/wp-content/uploads/2010/10/input-black.gif",
#             "Page displays solved captcha text within 15 seconds",
#         ],
#         "evaluation_url": "https://example.com/notify",
#         # "attachments": [{ "name": "sample.png", "url": "data:image/png;base64,iVBORw..." }]
#         "attachments": [{ "name": "sample.png", "url": "https://c22blog.wordpress.com/wp-content/uploads/2010/10/input-black.gif" }]
#         }

#     response = requests.post("http://localhost:8000/handle_task", json=payload)
#     print(response.json())





def send_task():
    payload = {
        "email": "student@example.com",
        "secret": "amazing1",
        "task": "Factorial-Calculator-...",
        "round": 2,
        "nonce": "ab12-...",
        "brief": "create a tool to find factorial of a given number by user, Theme Should be Simple and Professional.",
        "checks": [
            "Repo has MIT license",
            "README.md is professional",
            "Page displays to enter number to find factorial",
            "Page displays solved factorial of given number",
        ],
        "evaluation_url": "https://example.com/notify",
        "attachments": [{ "name": "sample.png", "url": "data:image/png;base64,iVBORw..." }]
        }

    # response = requests.post("http://localhost:8000/handle_task", json=payload)
    response = requests.post("https://amolpratap-p1.hf.space/handle_task", json=payload)
    print(response.json())











if __name__ == "__main__":
    send_task()