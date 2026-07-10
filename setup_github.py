"""
Script utilitario para configurar o repositorio GitHub localmente.

Como usar:
    python setup_github.py <SEU_TOKEN_GITHUB>

Gere um token em: https://github.com/settings/tokens
Permissao necessaria: repo
"""
import json
import subprocess
import sys
import urllib.request


def create_repo(token: str, user: str, repo: str, desc: str) -> str:
    data = json.dumps({"name": repo, "description": desc, "private": False}).encode()
    req = urllib.request.Request(
        "https://api.github.com/user/repos",
        data=data,
        headers={
            "Authorization": f"token {token}",
            "Content-Type": "application/json",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "setup-script",
        },
        method="POST",
    )
    import urllib.error
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())["clone_url"]
    except urllib.error.HTTPError as e:
        body = json.loads(e.read().decode())
        if e.code == 422 and "already exists" in str(body):
            return f"https://github.com/{user}/{repo}.git"
        print(f"Erro {e.code}: {body.get('message')}")
        sys.exit(1)


def main():
    if len(sys.argv) < 2:
        print("Uso: python setup_github.py <TOKEN_GITHUB>")
        sys.exit(1)

    token = sys.argv[1]
    user  = "TiagoMFernandes"
    repo  = "engenharia-dados-saneamento"
    desc  = (
        "Pipeline de engenharia de dados para analise de indicadores "
        "publicos de saneamento basico no Brasil."
    )

    import os
    cwd = os.path.dirname(os.path.abspath(__file__))

    print(f"Criando repositorio {repo}...")
    clone_url = create_repo(token, user, repo, desc)
    auth_url  = clone_url.replace("https://", f"https://{user}:{token}@")

    subprocess.run(["git", "remote", "remove", "origin"], cwd=cwd, capture_output=True)
    subprocess.run(["git", "remote", "add", "origin", auth_url], cwd=cwd, check=True)
    subprocess.run(["git", "push", "-u", "origin", "main"], cwd=cwd, check=True)

    print(f"\nConcluido! https://github.com/{user}/{repo}")


if __name__ == "__main__":
    main()
