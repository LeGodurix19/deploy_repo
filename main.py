import os
import subprocess
import shutil

def run_command(command, use_sudo=False):
    """Exécute une commande shell et affiche la sortie. Utilise sudo si nécessaire."""
    if use_sudo:
        command = f"sudo {command}"
    result = subprocess.run(command, shell=True, text=True, capture_output=True)
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        raise Exception(f"Command failed: {command}")
    return result.stdout

def clone_github_repo():
    """Demande un URL GitHub à cloner."""
    github_url = input("Enter the GitHub repository URL to clone: ").strip()
    project_name = github_url.split('/')[-1].replace('.git', '')
    
    # Clone the GitHub repository
    run_command(f"git clone {github_url}")
    
    # Change directory to the cloned project
    os.chdir(project_name)
    print(f"Cloned the repository {github_url} into {project_name}.")
    
    return project_name

def configure_env_file():
    """Configure le fichier .env à partir de .env_example."""
    if os.path.exists('.env_example'):
        shutil.copy('.env_example', '.env')
        print("Copied .env_example to .env.")
    else:
        print("No .env_example found.")
        return
    
    # Demander la configuration des variables .env
    external_port = input("Enter the external port for the application (default 5000): ").strip() or "5000"
    
    # Mettre à jour le fichier .env
    with open('.env', 'a') as env_file:
        env_file.write(f"EXTERNAL_PORT={external_port}\n")
        print(f"Configured EXTERNAL_PORT={external_port} in .env.")
    
    return external_port

def configure_nginx_http(domain_name, external_port):
    """Configure Nginx sans SSL (HTTP uniquement)."""
    nginx_config = f"""
server {{
    listen 80;
    server_name {domain_name};

    location / {{
        proxy_pass http://127.0.0.1:{external_port};
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }}

    access_log /var/log/nginx/{domain_name}_access.log;
    error_log /var/log/nginx/{domain_name}_error.log;
}}
"""
    nginx_config_path = f"/etc/nginx/sites-available/{domain_name}.conf"
    
    # Write the Nginx configuration (requires sudo)
    with open(nginx_config_path, 'w') as f:
        f.write(nginx_config)
    
    # Create a symbolic link in sites-enabled (requires sudo)
    run_command(f"ln -s {nginx_config_path} /etc/nginx/sites-enabled/", use_sudo=True)

    # Test Nginx configuration and reload (requires sudo)
    run_command("nginx -t && systemctl reload nginx", use_sudo=True)
    print(f"Nginx configuration for {domain_name} (HTTP only) created and reloaded.")

def configure_nginx_ssl(domain_name, external_port):
    """Configure Nginx avec SSL après génération du certificat."""
    nginx_config = f"""
server {{
    listen 80;
    server_name {domain_name};

    location / {{
        proxy_pass http://127.0.0.1:{external_port};
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }}

    access_log /var/log/nginx/{domain_name}_access.log;
    error_log /var/log/nginx/{domain_name}_error.log;
}}

server {{
    listen 443 ssl;
    server_name {domain_name};

    ssl_certificate /etc/letsencrypt/live/{domain_name}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/{domain_name}/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

    location / {{
        proxy_pass http://127.0.0.1:{external_port};
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }}
}}
"""
    nginx_config_path = f"/etc/nginx/sites-available/{domain_name}.conf"
    
    # Write the updated Nginx configuration (requires sudo)
    with open(nginx_config_path, 'w') as f:
        f.write(nginx_config)

    # Test Nginx configuration and reload (requires sudo)
    run_command("nginx -t && systemctl reload nginx", use_sudo=True)
    print(f"Nginx configuration for {domain_name} with SSL created and reloaded.")

def generate_ssl_certificate(domain_name):
    """Génère le certificat SSL avec Certbot."""
    print(f"Generating SSL certificate for {domain_name} using Certbot...")
    run_command(f"certbot --nginx -d {domain_name} --non-interactive --agree-tos -m hugoorickx@gmail.com", use_sudo=True)
    print(f"SSL certificate generated and applied for {domain_name}.")

def launch_docker_compose():
    """Lance le projet avec Docker Compose."""
    print("Launching the application using Docker Compose...")
    run_command("docker-compose up -d")
    print("Application is now running.")

def main():
    """Main script execution."""
    try:
        # Cloner le repo GitHub
        project_name = clone_github_repo()

        # Demander le domaine à configurer
        domain_name = input("Enter the domain name to link with the project (e.g., example.com): ").strip()

        # Configurer le fichier .env
        external_port = configure_env_file()

        # Configurer Nginx uniquement en HTTP
        configure_nginx_http(domain_name, external_port)

        # Générer le ce        git branch --set-upstream-to=origin/main mainrtificat SSL avec Certbot
        generate_ssl_certificate(domain_name)

        # Reconfigurer Nginx pour utiliser SSL après la génération du certificat
        configure_nginx_ssl(domain_name, external_port)

        # Lancer Docker Compose
        launch_docker_compose()

        print(f"Project {project_name} is successfully deployed and linked to {domain_name}.")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == '__main__':
    main()
