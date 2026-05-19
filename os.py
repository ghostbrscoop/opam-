import os
import subprocess
import requests
from tkinter import filedialog, Tk
from datetime import datetime
import time

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

def log_history(commit_id, message, files, folder):
    total_size = sum(os.path.getsize(f) for f in files)
    size_mb = round(total_size / (1024*1024), 2)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(os.path.join(folder, "history.txt"), "a", encoding="utf-8") as h:
        h.write(f"Commit ID: {commit_id}\n")
        h.write(f"Mensagem: {message}\n")
        h.write("Arquivos:\n")
        h.write(f"{'Nome':30} | {'Tamanho':10} | {'Modificado em'}\n")
        h.write("-"*60 + "\n")
        for f in files:
            size_kb = os.path.getsize(f) / 1024
            mod_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(os.path.getmtime(f)))
            h.write(f"{os.path.basename(f):30} | {size_kb:8.2f} KB | {mod_time}\n")
        h.write(f"Peso total: {size_mb} MB\n")
        h.write(f"Data/Hora: {now}\n")
        h.write("-"*40 + "\n")

def check_git_config():
    def get_config(key):
        try:
            return subprocess.check_output(["git", "config", "--get", key]).decode().strip()
        except subprocess.CalledProcessError:
            return None
    return get_config("user.name"), get_config("user.email")

def create_repo_github(token, repo_name):
    headers = {"Authorization": f"token {token}"}
    data = {"name": repo_name, "private": False}
    r = requests.post("https://api.github.com/user/repos", json=data, headers=headers)
    if r.status_code == 201:
        return r.json()["html_url"]
    else:
        raise Exception(r.json())

def handle_push(files, folder):
    # Detectar arquivos novos
    status = subprocess.check_output(["git", "status", "--porcelain"]).decode().splitlines()
    untracked = [line[3:] for line in status if line.startswith("??")]

    if untracked:
        print("Foram detectados arquivos novos. Selecione quais deseja incluir no merge...")
        Tk().withdraw()
        new_files = filedialog.askopenfilenames(
            title="Selecione os arquivos novos para incluir",
            initialdir=folder,
            filetypes=[("Todos os arquivos", "*.*")]
        )
        if new_files:
            subprocess.run(["git", "add"] + list(new_files))

    # Perguntar sobre merge ou substituição
    choice = input("Deseja 'substituir' na principal ou fazer 'merge' com a principal? ")
    if choice.lower() == "merge":
        subprocess.run(["git", "pull", "origin", "main", "--no-rebase"])
        subprocess.run(["git", "push"])
    elif choice.lower() == "substituir":
        subprocess.run(["git", "push", "-f", "origin", "main"])
    else:
        print("Opção inválida, não foi feito push.")

def end_flow():
    print("\nOperação concluída.")
    choice = input("Deseja encerrar o programa? (y/n): ").strip().lower()
    if choice == "y":
        print("Encerrando...")
        exit()
    else:
        main()  # reinicia o programa
def option0():
    repo_link = input("Digite o link do repositório para clonar: ")
    print("Agora escolha a pasta onde deseja clonar o repositório...")
    Tk().withdraw()
    folder = filedialog.askdirectory(title="Escolha a pasta onde deseja clonar o repositório")
    print(f"Clonando {repo_link} em {folder}...")
    subprocess.run(["git", "clone", repo_link, folder])
    print("Repositório clonado com sucesso!")
    end_flow()

def option1(token):
    repo_name = input("Digite o nome do repositório: ")
    if input(f"Confirmar '{repo_name}'? (y/n): ") != "y":
        return

    print("Agora escolha a pasta onde o repositório será criado...")
    Tk().withdraw()
    folder = filedialog.askdirectory(title="Escolha a pasta para o repositório")

    print("Agora escolha os arquivos que deseja enviar...")
    files = filedialog.askopenfilenames(title="Selecione os arquivos para subir")

    print("\nArquivos selecionados:")
    for f in files:
        size_kb = os.path.getsize(f) / 1024
        mod_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(os.path.getmtime(f)))
        print(f"- {os.path.basename(f)} | {size_kb:.2f} KB | modificado em {mod_time}")

    user, email = check_git_config()
    if not user:
        user = input("Digite seu nome de usuário Git: ")
        subprocess.run(["git", "config", "--global", "user.name", user])
    if not email:
        email = input("Digite seu email Git: ")
        subprocess.run(["git", "config", "--global", "user.email", email])

    repo_url = create_repo_github(token, repo_name)

    os.chdir(folder)
    subprocess.run(["git", "init"])
    subprocess.run(["git", "remote", "add", "origin", repo_url])
    subprocess.run(["git", "add"] + list(files))

    commit_msg = input("Digite a mensagem do commit: ")
    subprocess.run(["git", "commit", "-m", commit_msg])
    subprocess.run(["git", "branch", "-M", "main"])
    subprocess.run(["git", "push", "-u", "origin", "main"])

    commit_id = subprocess.check_output(["git", "rev-parse", "HEAD"]).decode().strip()
    log_history(commit_id, commit_msg, files, folder)

    print("Repositório criado:", repo_url)
    end_flow()

def option2():
    print("Agora escolha a pasta do repositório...")
    Tk().withdraw()
    folder = filedialog.askdirectory(title="Escolha a pasta do repositório")

    print("Agora escolha os arquivos para commit...")
    files = filedialog.askopenfilenames(title="Selecione os arquivos para commit")

    print("\nArquivos selecionados:")
    for f in files:
        size_kb = os.path.getsize(f) / 1024
        mod_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(os.path.getmtime(f)))
        print(f"- {os.path.basename(f)} | {size_kb:.2f} KB | modificado em {mod_time}")

    os.chdir(folder)
    subprocess.run(["git", "add"] + list(files))
    commit_msg = input("Digite a mensagem do commit: ")

    status = subprocess.check_output(["git", "status", "--porcelain"]).decode().strip()
    if not status:
        print("Nenhuma alteração detectada. Nada para commitar.")
    else:
        subprocess.run(["git", "commit", "-m", commit_msg])
        if input("Deseja dar push? (y/n): ") == "y":
            handle_push(files, folder)
        commit_id = subprocess.check_output(["git", "rev-parse", "HEAD"]).decode().strip()
        log_history(commit_id, commit_msg, files, folder)

    end_flow()

def main():
    print(ASCII_ART)
    print("Escolha uma opção:")
    print("0 - Clonar repositório existente")
    print("1 - Inicializar e criar repositório")
    print("2 - Fazer commit normal")

    choice = input("Opção: ")

    token = os.getenv("GITHUB_TOKEN")
    if not token:
        print("Token não encontrado no ambiente. Configure com setx ou insira manualmente.")
        token = input("Digite seu token GitHub: ")

    if choice == "0":
        option0()
    elif choice == "1":
        option1(token)
    elif choice == "2":
        option2()
    else:
        print("Opção inválida.")
        end_flow()

if __name__ == "__main__":
    main()

