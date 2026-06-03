import os
import sys
import threading
import socket
import tkinter as tk
from tkinter import messagebox, simpledialog
from daphne.server import Server
from daphne.endpoints import build_endpoint_description_strings
import webbrowser
import qrcode
from PIL import Image, ImageTk
import urllib.request
import json
import subprocess
import time

CURRENT_VERSION = "v1.0.5"

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

# Setup Django globally before GUI so imports work
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()
from django.core.management import call_command
from django.core.wsgi import get_wsgi_application

def run_migrations():
    try:
        import sys
        import io
        # Redirect stdout/stderr so Django doesn't crash when printing in noconsole mode
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = io.StringIO()
        sys.stderr = io.StringIO()
        try:
            call_command('migrate')
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr
        messagebox.showinfo("Success", "Database setup completed successfully.")
    except Exception as e:
        messagebox.showerror("Error", f"Migration failed:\n{e}")

def create_superuser():
    try:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        phone_number = simpledialog.askstring("Admin User", "Enter phone number:")
        if not phone_number: return
        name = simpledialog.askstring("Admin User", "Enter full name:")
        if not name: return
        password = simpledialog.askstring("Admin User", "Enter admin password:", show='*')
        if not password: return
        
        if User.objects.filter(phone_number=phone_number).exists():
            messagebox.showerror("Error", "This user already exists!")
            return
            
        User.objects.create_superuser(phone_number=phone_number, name=name, password=password)
        messagebox.showinfo("Success", f"Admin '{name}' successfully created!")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to create admin user:\n{e}")

server_started = False

def run_app(local_ip):
    global server_started
    
    # Start Django Waitress Server if not already running
    if not server_started:
        import config.asgi
        def start_server():
            endpoints = build_endpoint_description_strings(host='0.0.0.0', port=8000)
            server = Server(application=config.asgi.application, endpoints=endpoints)
            server.run()
        threading.Thread(target=start_server, daemon=True).start()
        server_started = True

    # Open Default Web Browser
    webbrowser.open('http://127.0.0.1:8000')

def update_application(root):
    try:
        req = urllib.request.Request("https://api.github.com/repos/ibrohim2911/X-store/releases/latest")
        req.add_header('User-Agent', 'X-Store-Updater')
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            latest_version = data.get('tag_name')
            assets = data.get('assets', [])
            
        if not latest_version:
            messagebox.showinfo("Update", "Could not check for updates.")
            return
            
        if latest_version == CURRENT_VERSION:
            messagebox.showinfo("Update", "You are already using the latest version.")
            return
            
        if not assets:
            messagebox.showinfo("Update", f"Version {latest_version} is available, but no executable was found in the release.")
            return
            
        download_url = assets[0].get('browser_download_url')
        
        if messagebox.askyesno("Update Available", f"A new version ({latest_version}) is available!\n\nDo you want to download and install it now?"):
            from tkinter import ttk
            import threading
            
            # Show a downloading window
            progress_win = tk.Toplevel(root)
            progress_win.title("Downloading Update")
            progress_win.geometry("350x150")
            tk.Label(progress_win, text=f"Downloading {latest_version}...").pack(pady=(20, 10))
            
            progress_var = tk.DoubleVar()
            progress_bar = ttk.Progressbar(progress_win, variable=progress_var, maximum=100)
            progress_bar.pack(fill='x', padx=20)
            
            progress_label = tk.Label(progress_win, text="0%")
            progress_label.pack(pady=5)
            
            progress_win.update()

            def run_download():
                try:
                    if getattr(sys, 'frozen', False):
                        current_exe_path = sys.executable
                    else:
                        current_exe_path = os.path.abspath("XStore.exe")
                        
                    exe_dir = os.path.dirname(current_exe_path)
                    update_exe_path = os.path.join(exe_dir, "XStore_update.exe")
                    
                    def reporthook(blocknum, blocksize, totalsize):
                        readso_far = blocknum * blocksize
                        if totalsize > 0:
                            percent = (readso_far * 100) / totalsize
                            if percent > 100: percent = 100
                            root.after(0, lambda p=percent: progress_var.set(p))
                            root.after(0, lambda p=percent: progress_label.config(text=f"{int(p)}%"))

                    urllib.request.urlretrieve(download_url, update_exe_path, reporthook)
                    
                    root.after(0, finalize_update, current_exe_path, update_exe_path, exe_dir)
                except Exception as e:
                    root.after(0, progress_win.destroy)
                    root.after(0, lambda err=e: messagebox.showerror("Download Error", f"Failed to download update:\n{str(err)}"))

            def finalize_update(current_exe_path, update_exe_path, exe_dir):
                progress_win.destroy()
                bat_path = os.path.join(exe_dir, "updater.bat")
                
                with open(bat_path, "w") as f:
                    f.write(f'''@echo off
cd /d "{exe_dir}"
:wait
timeout /t 1 /nobreak > NUL
del "{current_exe_path}"
if exist "{current_exe_path}" goto wait
move /y "{update_exe_path}" "{current_exe_path}"
start "" "{current_exe_path}"
del "%~f0"
''')
                # Launch batch file hidden and exit
                CREATE_NO_WINDOW = 0x08000000
                subprocess.Popen([bat_path], shell=True, creationflags=CREATE_NO_WINDOW)
                sys.exit(0)

            threading.Thread(target=run_download, daemon=True).start()
            
    except Exception as e:
        messagebox.showerror("Update Error", f"Failed to check for updates:\n{str(e)}")

def main():
    local_ip = get_local_ip()
    url = f"http://{local_ip}:8000"

    root = tk.Tk()
    root.title("X-Store Launcher")
    root.geometry("400x560")
    root.configure(bg="#f8fafc")
    
    # Title
    tk.Label(root, text="X-Store POS", font=("Helvetica", 20, "bold"), bg="#f8fafc").pack(pady=(20, 5))
    tk.Label(root, text="Scan to access from your phone:", font=("Helvetica", 10), bg="#f8fafc").pack()
    tk.Label(root, text=url, font=("Helvetica", 10, "bold"), fg="#4f46e5", bg="#f8fafc").pack(pady=(0, 10))

    # QR Code
    try:
        qr = qrcode.QRCode(box_size=5, border=2)
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
        qr_photo = ImageTk.PhotoImage(img)

        qr_label = tk.Label(root, image=qr_photo, bg="#f8fafc")
        qr_label.image = qr_photo
        qr_label.pack(pady=10)
    except Exception as e:
        tk.Label(root, text="(QR Code failed to generate)", bg="#f8fafc", fg="red").pack(pady=10)

    # Actions
    tk.Button(root, text="1. Setup / Update Database", font=("Helvetica", 10, "bold"), width=30, height=2, 
              bg="#e2e8f0", command=run_migrations).pack(pady=5)
    tk.Button(root, text="2. Create Admin User", font=("Helvetica", 10, "bold"), width=30, height=2, 
              bg="#e2e8f0", command=create_superuser).pack(pady=5)
    tk.Button(root, text="3. Check for Updates", font=("Helvetica", 10, "bold"), width=30, height=2, 
              bg="#e2e8f0", command=lambda: update_application(root)).pack(pady=5)
    
    tk.Button(root, text="Launch POS System", font=("Helvetica", 12, "bold"), width=25, height=2, 
              bg="#4f46e5", fg="white", command=lambda: run_app(local_ip)).pack(pady=15)

    root.mainloop()

if __name__ == '__main__':
    main()
