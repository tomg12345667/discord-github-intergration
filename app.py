from flask import Flask, request, redirect, render_template_string, session, jsonify
import requests
import json
import os

app = Flask(__name__)
app.secret_key = "CHANGE_THIS_SECRET_KEY"

DISCORD_WEBHOOK = "YOUR_DISCORD_WEBHOOK"

CONFIG_FILE = "config.json"

# ------------------------
# default config
# ------------------------
DEFAULT_CONFIG = {
    "push": True,
    "issues": True,
    "pull_request": True,
    "repository": True
}


def load_config():
    if not os.path.exists(CONFIG_FILE):
        save_config(DEFAULT_CONFIG)
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)


def save_config(cfg):
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)


def send(msg):
    requests.post(DISCORD_WEBHOOK, json={"content": msg})


# ------------------------
# LOGIN (simple)
# ------------------------
USERNAME = "admin"
PASSWORD = "change_this_password"

def logged_in():
    return session.get("auth") == True


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form["username"] == USERNAME and request.form["password"] == PASSWORD:
            session["auth"] = True
            return redirect("/")
        return "Invalid login", 403

    return '''
    <form method="post">
        <input name="username" placeholder="username">
        <input name="password" type="password" placeholder="password">
        <button>Login</button>
    </form>
    '''


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


# ------------------------
# DASHBOARD
# ------------------------
@app.route("/")
def dashboard():
    if not logged_in():
        return redirect("/login")

    cfg = load_config()

    return render_template_string("""
    <h2>GitHub → Discord Control Panel</h2>

    <form method="post" action="/update">
        <label><input type="checkbox" name="push" {% if push %}checked{% endif %}> Push</label><br>
        <label><input type="checkbox" name="issues" {% if issues %}checked{% endif %}> Issues</label><br>
        <label><input type="checkbox" name="pull_request" {% if pull_request %}checked{% endif %}> PRs</label><br>
        <label><input type="checkbox" name="repository" {% if repository %}checked{% endif %}> Repo Created</label><br>
        <button type="submit">Save</button>
    </form>

    <br>
    <a href="/logout">Logout</a>
    """, **cfg)


@app.route("/update", methods=["POST"])
def update():
    if not logged_in():
        return redirect("/login")

    cfg = {
        "push": "push" in request.form,
        "issues": "issues" in request.form,
        "pull_request": "pull_request" in request.form,
        "repository": "repository" in request.form,
    }

    save_config(cfg)
    return redirect("/")


# ------------------------
# GITHUB WEBHOOK
# ------------------------
@app.route("/github", methods=["POST"])
def github():
    cfg = load_config()
    event = request.headers.get("X-GitHub-Event")
    data = request.json

    if event == "ping":
        send("GitHub webhook connected ✅")
        return jsonify({"ok": True})

    if event == "push" and cfg["push"]:
        repo = data["repository"]["full_name"]
        branch = data["ref"].split("/")[-1]
        send(f"🚀 Push: **{repo}** ({branch})")

    elif event == "issues" and cfg["issues"]:
        issue = data["issue"]
        send(f"🐛 Issue: #{issue['number']} {issue['title']}")

    elif event == "pull_request" and cfg["pull_request"]:
        pr = data["pull_request"]
        send(f"🔀 PR: #{pr['number']} {pr['title']}")

    elif event == "repository" and cfg["repository"]:
        repo = data["repository"]
        if not repo.get("private", True):
            send(f"📦 New public repo: **{repo['full_name']}**")

    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
