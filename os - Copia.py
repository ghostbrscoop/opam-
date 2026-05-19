import os
import subprocess
import requests
from tkinter import filedialog, Tk

ASCII_ART = r"""
                                         :+#%%%@@@@@@%%##=.                                         
                                     =%%@@@@@@@@@@@@@@@@@@@@@%-                                     
                                  =%%@@@@@@@@@@@@@@@@@@@@@@@@@@%%-                                  
                                *@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@%+                                
                              +%%@@@%--+%%@@@@@@@@@@@@@@@@%#=-=%@@@%%=                              
                            .%@@@@@%*      :-.        .=:      *@@@@@%#                             
                           .%@@@@@@@+                          *@@@@@@%%.                           
                           %@@@@@@@%*                          #%@@@@@@@*                           
                          +@@@@@@@%:                            +@@@@@@%%-                          
                          %@@@@@@@*                              #%@@@@@@#                          
                         .%@@@@@@@+                              *@@@@@@@%                          
                         .%@@@@@@%*                              %@@@@@@@%                          
                          #@@@@@@@%-                            +@@@@@@@@*                          
                          :%@@@@@@@%=                          +@@@@@@@%%                           
                           =@@@@@@@@%%+                      *%@@@@@@@@%=                           
                            *%@@*  .#%@@@@%#+.        :+#%@@@@@@@@@@@@%+                            
                             -%@@%#. -%%@@@%.          =@@@@@@@@@@@@%%:                             
                               *%@@%:                   %@@@@@@@@@@%+                               
                                 *%%%%*+=--=            %@@@@@@@@%+                                 
                                   :%%@@@@@#            %@@@@@%#                                    
                                       +#%%#            %%%#-                                       
"""

def check_git_config():
    try:
        user = subprocess.check_output(["git", "config", "--get", "user.name"]).decode().strip()
    except subprocess.CalledProcessError:
        user = None
    try:
        email = subprocess.check_output(["git", "config", "--get", "user.email"]).decode().strip()
    except subprocess.CalledProcessError:
        email = None
    return user, email

def create_repo_github(token, repo_name):
    headers = {"Authorization": f"token {token}"}
    data = {"name": repo_name, "private": False}
    r = requests.post("https://api.github.com/user/repos", json=data, headers=headers)
    if r.status_code == 201:
        return r.json()["html_url"]
    else:
        raise Exception(r.json())

def main():
    repo_name = input("Digite o nome do repositório: ")
    if input(f"Confirmar '{repo_name}'? (y/n): ") != "y":
        return

    # escolher pasta
    Tk().withdraw()
    folder = filedialog.askdirectory(title="Escolha a pasta para o repositório")
    if input(f"Confirmar pasta '{folder}'? (y/n): ") != "y":
        return

    # escolher arquivos
    files = filedialog.askopenfilenames(title="Selecione os arquivos para subir")

    # verificar git config
    user, email = check_git_config()
    if not user:
        user = input("Digite seu nome de usuário Git: ")
        subprocess.run(["git", "config", "--global", "user.name", user])
    if not email:
        email = input("Digite seu email Git: ")
        subprocess.run(["git", "config", "--global", "user.email", email])

    token = os.getenv("GITHUB_TOKEN") or input("Digite seu token GitHub: ")
    repo_url = create_repo_github(token, repo_name)

    # inicializar git
    os.chdir(folder)
    subprocess.run(["git", "init"])
    subprocess.run(["git", "remote", "add", "origin", repo_url])
    subprocess.run(["git", "add"] + list(files))

    commit_msg = input("Digite a mensagem do commit: ")
    subprocess.run(["git", "commit", "-m", commit_msg])
    subprocess.run(["git", "branch", "-M", "main"])

    if input("Deseja dar push para 'main'? (y/n): ") == "y":
        subprocess.run(["git", "push", "-u", "origin", "main"])

    print("Repositório criado:", repo_url)
    print(ASCII_ART)

if __name__ == "__main__":
    main()
